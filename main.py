"""
This script processes GKE cluster upgrade-related notifications as part of a GCP Cloud Function.
"""
# =============================================================================
# Imports
# =============================================================================
import base64
import json
import os
import requests
import sys
import logging
import google.cloud.logging
from google.cloud import secretmanager


def process_gke_notification_event(event, gke_slack_notification_channel):
    if "data" in event:
        # Shared Variables
        cluster = event["attributes"]["cluster_name"]
        cluster_resource = json.loads(event["attributes"]["payload"])["resourceType"]
        location = event["attributes"]["cluster_location"]
        message = base64.b64decode(event["data"]).decode("utf-8")
        project = event["attributes"]["project_id"]

        # UpgradeEvent
        if "UpgradeEvent" in event["attributes"]["type_url"]:
            current_version = json.loads(event["attributes"]["payload"])["currentVersion"]
            start_time = json.loads(event["attributes"]["payload"])["operationStartTime"]
            target_version = json.loads(event["attributes"]["payload"])["targetVersion"]
            title = f"GKE Cluster Upgrade Notification :zap:"
            slack_data = {
                "username": "GKE Notifications",
                "icon_emoji": ":kubernetes:",
                "channel": gke_slack_notification_channel,
                "attachments": [
                    {
                        "color": "#9733EE",
                        "fields": [
                            {"title": title},
                            {
                                "title": "Project",
                                "value": project,
                                "short": "false",
                            },
                            {
                                "title": "Cluster",
                                "value": cluster,
                                "short": "false",
                            },
                            {
                                "title": "Location",
                                "value": location,
                                "short": "false",
                            },
                            {
                                "title": "Update Type",
                                "value": cluster_resource,
                                "short": "false",
                            },
                            {
                                "title": "Current Version",
                                "value": current_version,
                                "short": "false",
                            },
                            {
                                "title": "Target Version",
                                "value": target_version,
                                "short": "false",
                            },
                            {
                                "title": "Start Time",
                                "value": start_time,
                                "short": "false",
                            },
                            {
                                "title": "Details",
                                "value": message,
                                "short": "false",
                            },
                        ],
                    }
                ],
            }
            return slack_data
        # UpgradeAvailableEvent
        elif "UpgradeAvailableEvent" in event["attributes"]["type_url"]:
            available_version = json.loads(event["attributes"]["payload"])["version"]
            release_channel = json.loads(event["attributes"]["payload"])["releaseChannel"]
            title = f"GKE Cluster Upgrade Available Notification :zap:"
            slack_data = {
                "username": "GKE Notifications",
                "icon_emoji": ":kubernetes:",
                "channel": gke_slack_notification_channel,
                "attachments": [
                    {
                        "color": "#4F7942",
                        "fields": [
                            {"title": title},
                            {
                                "title": "Project",
                                "value": project,
                                "short": "false",
                            },
                            {
                                "title": "Cluster",
                                "value": cluster,
                                "short": "false",
                            },
                            {
                                "title": "Location",
                                "value": location,
                                "short": "false",
                            },
                            {
                                "title": "Eligible Resource",
                                "value": cluster_resource,
                                "short": "false",
                            },
                            {
                                "title": "Eligible Version",
                                "value": available_version,
                                "short": "false",
                            },
                            {
                                "title": "Details",
                                "value": message,
                                "short": "false",
                            },
                        ],
                    }
                ],
            }
            return slack_data
        else:
            logging.info("Event was neither UpgradeEvent or UpgradeAvailableEvent, so it will be skipped.")
    else:
        logging.info("No event was passed into the function. Exiting.")

def get_secrets(project_id, secret_name, version_id="latest") -> str:
    client = secretmanager.SecretManagerServiceClient()
    secret_name = f'projects/{project_id}/secrets/{secret_name}/versions/{version_id}'
    response = client.access_secret_version(request={"name": secret_name})
    gcp_secret = response.payload.data.decode("UTF-8")
    return gcp_secret


def send_notification_to_slack(event, context):
    """Background Cloud Function to be triggered by Pub/Sub.
    For sample messages refer to the json inputs in tests.
    """
    if os.getenv('CLOUD_LOGGING_ENABLED'): #Sending logs only when running in GCP and skipping it for local
        client = google.cloud.logging.Client()
        client.setup_logging()
    try:
        logging.info("""This Function was triggered by messageId {} published at {}""".format(context.event_id, context.timestamp))
        slack_webhook_url = get_secrets(os.environ["PROJECT_ID"], os.environ['SLACK_SECRET_NAME'])
        gke_slack_notification_channel = os.environ['SLACK_NOTIFICATION_CHANNEL']
        # Print the event at the beginning for easier debug.
        logging.info("Event was passed into function and will be processed.")
        logging.info(event)
        slack_data = process_gke_notification_event(event, gke_slack_notification_channel)
        byte_length = str(sys.getsizeof(slack_data))
        headers = {
            "Content-Type": "application/json",
            "Content-Length": byte_length,
        }
        response = requests.post(slack_webhook_url, data=json.dumps(slack_data), headers=headers)
        if response.status_code != 200:
            logging.error(f"Failed to send the notification to slack '{response.status_code, response.text}'")
            raise Exception(response.status_code, response.text)
        else:
            logging.info("GKE Upgrade notification is successfully processed")
            return response
    except Exception as exception:
        logging.error(f"Failed to process the GKE upgrade event '{event}'")
        logging.error(exception)

##local development test configuration
class Context(object):
    pass

if __name__ == "__main__":
    os.environ['SLACK_SECRET_NAME'] = "slack-webhook-url"
    os.environ['SLACK_NOTIFICATION_CHANNEL'] = "#gke-notifications-test-chimbu"
    os.environ['CLOUD_LOGGING_ENABLED'] = "false"
    os.environ["PROJECT_ID"] = "sandbox"
    upgrade_notification_event = {
        "@type": "type.googleapis.com/google.pubsub.v1.PubsubMessage",
        "attributes": {
            "cluster_location": "europe-west2",
            "cluster_name": "sandbox-gke-cluster",
            "payload": "{\"resourceType\":\"MASTER\",\"operation\":\"operation-1645107677624-ab05d433\","
                       "\"operationStartTime\":\"2022-02-17T14:21:17.624225580Z\","
                       "\"currentVersion\":\"1.21.5-gke.1802\",\"targetVersion\":\"1.21.6-gke.1500\"}",
            "project_id": "4325342324",
            "type_url": "type.googleapis.com/google.container.v1beta1.UpgradeEvent"
        },
        "data": "VGhpcyBpcyBhIHRlc3Qgbm90aWZpY2F0aW9uCg=="
    }
    context1 = Context()
    context1.event_id = '4111677166000558'
    context1.timestamp = '2022-02-17T14:21:18.801Z'
    send_notification_to_slack(upgrade_notification_event, context1)
