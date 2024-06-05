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
1. Copy [tpt.py](composer/tpt.py) into the Composer dags folder
1. Copy [export.tpt](composer/export.tpt) into the Composer data folder

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
# Run interactive bash shell within the TPT Docker Image
sudo docker run -it --entrypoint bash -e "accept_license=Y" teradata/tpt:latest
```

```bash
# Run tbuild command within the TPT Docker Image
sudo docker run \
  --entrypoint tbuild \
  -v ./export.tpt:/tmp/export.tpt \
  -v ./credentials.json:/root/.gcs/credentials \
  -e "accept_license=Y" \
  teradata/tpt:latest \
  -f /tmp/export.tpt \
  -u "TD_HOSTNAME='10.128.0.26',TD_USERNAME='dbc',TD_PASSWORD='pass'"
```

```bash
# Run tbuild command within the TPT Docker Image using bash
sudo docker run \
  --entrypoint bash \
  -v ./export.tpt:/tmp/export.tpt \
  -v ./credentials.json:/root/.gcs/credentials \
  -e "accept_license=Y,PASS=pass"  \
  teradata/tpt:latest \
  -cx "tbuild \
  -f /tmp/export.tpt \
  -u \"TD_HOSTNAME='10.128.0.26',TD_USERNAME='dbc',TD_PASSWORD='${PASS}'\""
```

# What's inside the TPT Docker Image?

Teradata's [TPT docker image](https://hub.docker.com/r/teradata/tpt) comes packaged with the following:
* Teradata Parallel Transporter Base
* Teradata CLIv2
* Shared ICU Libraries for Teradata
* Teradata Wallet
* Teradata BTEQ
* Teradata Access Modules

# Tuning TPT Parameters

## Operator instances:
 * The number of sessions specified by the value of the operator MaxSessions attribute are balanced across the number of operator instances. 
 * If the number of instances is not specified, the default is 1 instance per operator.
 * Start by specifying only one or two instances for any given operator.
Teradata PT will start as many instances as specified, but it uses only as many as needed.
 * Don't create more instances than needed--instances consume system resources.
 * Read the Teradata PT log file, which displays statistics showing how much data was processed by each instance. Reduce the number of instances if you see under utilized instances of any operators. If all instances are used add more and see if the job runs better.
 * If the number of instances exceeds the number of available sessions, the job aborts. Therefore, when specifying multiple instances make sure the MaxSessions attribute is set to a high enough value that there is at least one session per instance.
## MaxSessions:
 * If no value is set for MaxSessions, the operator attempts to connect to one session per available AMP.
 * If the value of the MaxSessions attribute for an operator is smaller than the number of operator instances, the job will abort.
 * If the value of MaxSessions is set to a number greater than the number of available AMPs, the job runs successfully, but logs on only as many sessions as available AMPs.
 * For some jobs, especially those running on systems with a large number of AMPS, the default session allocation (one per available database system AMP) may not be advantageous, and you may need to adjust the MaxSessions attribute value to limit the number of sessions used. After the job has run, use the evaluation criteria shown in Strategies for Balancing Sessions and Instances to help adjust and optimize the MaxSessions setting