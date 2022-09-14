# # gke-notifications-to-slack 

A Cloud Function that will parse the GKE cluster upgrade notifications and send them to a slack channel. Inspired by https://github.com/shipwreckdev/gke-notification-handler, Added support to retrieve secrets from the GCP secret manager and improved logging

## Configurations

This cloud function gets triggered once a new gke upgrade notification message is placed in the pub/sub topic. The gke notification pub/sub topic needs to be avaiable in the same project where the GKE cluster is created.

You'll need a Slack application with an incoming webhook token that has permission to post in whichever channel you'd like to receive these notifications.

## Prerequisites

- You must have a Pub/Sub topic available to handle notifications from a given GKE cluster, This can be created via UI/CLI/API or Terraform
- You must also configure your cluster to send notifications to the topic when upgrade events are triggered. This is currently available for configuration via Terraform in the google-beta provider/UI/CLI. Refer to https://cloud.google.com/kubernetes-engine/docs/concepts/cluster-notifications#enabling_upgrade_notifications for more details

### Python script

#### Source

- `main.py` - The python script processes the event received from pub/sub topic and publishes the messages to the slack channel.

- `requirements.txt` - libraries required for this python script. The requirements.txt and main.py need to be under the same directory.

The instructions listed on this page https://cloud.google.com/logging/docs/setup/python#connecting_the_library_to_python_logging is configured in the python script to capture the logs emitted by the application and send them to cloud logging.

### Environment Variables

The below environment variables passed to the cloud-function

- `PROJECT_ID` - GCP secret manager project id
- `SLACK_SECRET_NAME` - GCP secret manager secret name
- `SLACK_NOTIFICATION_CHANNEL` - Slack channel name
- `CLOUD_LOGGING_ENABLED` - Set to `true` to capture the logs emitted by the application and send them to cloud logging