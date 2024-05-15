# How to run TPT in Cloud Build

1. Create a private worker pool in Cloud Build named "tpt" in the us-central1 region which has network connectivity to your Teradata instance.

    > Note: It can be in any region, but this example uses us-central1.

1. Clone this repo and run the following:
    ```bash
    gcloud builds submit --region=us-central1 . \
        --substitutions=_SELECT_STATEMENT="SELECT * FROM tpch.orders;",_GCS_BUCKET="YOUR_BUCKET",_GCS_PREFIX="orders/"
    ```

## Running TPT Docker Image Locally

```bash
sudo docker run \
  --entrypoint tbuild \
  -v ./export.tpt:/tmp/export.tpt \
  -v ./credentials.json:/root/.gcs/credentials \
  -e "accept_license=Y" \
  teradata/tpt:latest \
  -f /tmp/export.tpt \
  -u "jobvar_tdpid='10.128.0.26',jobvar_username='dbc',jobvar_password='pass'"
```