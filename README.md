# How to run TPT in Composer

1. Create Composer Instance
1. Get the Composer GKE Cluster credentials for executing kubectl
   ```bash
   gcloud container clusters get-credentials CLUSTER_NAME \
     --region us-central1 \
     --project YOUR_PROJECT_ID
   ```
1. [Create a Kubernetes secret](https://kubernetes.io/docs/tasks/configmap-secret/managing-secret-using-kubectl/#use-raw-data) in the Composer GKE Cluster using the following command:
    ```bash
    kubectl create secret generic tpt-secrets \
      --namespace=composer-user-workloads \
      --from-literal=TERADATA_PASSWORD=YOUR_TD_PASSWORD \
      --from-literal=GCS_ACCESS_KEY_ID=srvcacct@YOUR_PROJECT_ID.iam.gserviceaccount.com \
      --from-literal=GCS_SECRET_ACCESS_KEY='-----BEGIN PRIVATE KEY-----\n ... \n-----END PRIVATE KEY-----\n'
    ```
1. Copy the [tpt.py](composer/tpt.py) DAG and the [export.tpt](composer/export.tpt) file into the Composer DAGs folder
# How to run TPT in Cloud Build

1. Create a private worker pool in Cloud Build named "tpt" in the us-central1 region which has network connectivity to your Teradata instance.

    > Note: It can be in any region, but this example uses us-central1.

1. Clone this repo and run the following:
    ```bash
    gcloud builds submit \
        --region=us-central1 . \
        --substitutions=_TERADATA_HOSTNAME="YOUR_TD_HOSTNAME",_SELECT_STATEMENT="SELECT * FROM tpch.orders;",_GCS_BUCKET="YOUR_BUCKET",_GCS_PREFIX="orders/"
    ```

# How to run TPT Docker Image Locally

```bash
docker run \
  --entrypoint tbuild \
  -v ./export.tpt:/tmp/export.tpt \
  -v ./credentials.json:/root/.gcs/credentials \
  -e "accept_license=Y" \
  teradata/tpt:latest \
  -f /tmp/export.tpt \
  -u "jobvar_tdpid='10.128.0.26',jobvar_username='dbc',jobvar_password='pass'"


  sudo docker run --entrypoint bash -v ./export.tpt:/tmp/export.tpt -v ./credentials.json:/root/.gcs/credentials -e "accept_license=Y,PASS=dbc"  teradata/tpt:latest -cx "tbuild -f /tmp/export.tpt -u \"jobvar_tdpid='10.128.0.26',jobvar_username='dbc',jobvar_password='${PASS}'\""
```

# What's inside the TPT Docker Image?

Teradata's [TPT docker image](https://hub.docker.com/r/teradata/tpt) comes packaged with the following:
* Teradata Parallel Transporter Base
* Teradata CLIv2
* Shared ICU Libraries for Teradata
* Teradata Wallet
* Teradata BTEQ
* Teradata Access Modules