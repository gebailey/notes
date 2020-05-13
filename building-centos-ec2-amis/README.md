# Building CentOS AMIs

These steps detail how to build AMIs that can be started on AWS EC2 instances
using cloud images provided by CentOS.

## Prerequisites


* An Amazon EC2 instance with sufficient disk space (~15GB) to run this script.
  I run this script on an EC2 instance running Amazon Linux 2 because the
  transfer speeds are much faster to S3.
* AWS credentials with permissions to create snapshots, etc.
* The `qemu-img` RPM installed.

## S3 Bucket

You'll need an S3 bucket to hold raw disk images that are used by the snapshot
creation process.

To create a bucket, use the following (this example assumes the `us-west-2`
region):

```
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="${ACCOUNT}-vm-imports"
BUCKET_REGION="us-west-2"

aws s3api create-bucket \
    --bucket ${BUCKET_NAME} \
    --create-bucket-configuration LocationConstraint=${BUCKET_REGION}
```

## IAM Role

AWS requires a `vmimport` role to be defined for import/export operations.  See
[this
documentation](https://docs.aws.amazon.com/vm-import/latest/userguide/vmie_prereqs.html#vmimport-role)
for more information.

If you don't have this role, it can be created using the following commands:

```
aws iam create-role --role-name vmimport --assume-role-policy-document "file://trust-policy.json"
```

Add a policy to the newly created role:

```
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="${ACCOUNT}-vm-imports"
sed -e "s/___BUCKET_NAME___/${BUCKET_NAME}/g" role-policy.json.template > role-policy.json
aws iam put-role-policy --role-name vmimport --policy-name vmimport --policy-document "file://role-policy.json"
```

## Upload raw disk image to S3

* Environment variables

  The following environment variables should be set for the subsequent steps:

  ```
  ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
  BUCKET_NAME="${ACCOUNT}-vm-imports"

  IMAGE_URL="http://cloud.centos.org/centos/8/x86_64/images/CentOS-8-ec2-8.1.1911-20200113.3.x86_64.qcow2"
  IMAGE_FILE="CentOS-8-ec2-8.1.1911-20200113.3.x86_64.qcow2"
  IMAGE_ID="CentOS-8-ec2-8.1.1911-20200113.3"
  IMAGE_DESCRIPTION="CentOS 8 ec2 8.1.1911 20200113.3"
  ```

* Download the image provided by CentOS:

  ```
  wget ${IMAGE_URL}
  ```

* Convert the provided qcow2 file to raw format:

  ```
  qemu-img convert -S 0 -p ${IMAGE_FILE} -O raw ${IMAGE_ID}.raw
  ```

* Run dracut on the raw image (required for CentOS 8, optional for CentOS 7):

  This step requires root level permissions.

  ```
  IMAGE_ID="CentOS-8-ec2-8.1.1911-20200113.3"

  mount -o loop,offset=1048576 ${IMAGE_ID}.raw /mnt
  mount -o bind /dev /mnt/dev
  mount -o bind /proc /mnt/proc
  mount -o bind /sys /mnt/sys
  mount -t tmpfs tmpfs /mnt/run

  chroot /mnt
  dracut -f /boot/initramfs-4.18.0-147.3.1.el8_1.x86_64.img 4.18.0-147.3.1.el8_1.x86_64
  # Run any other customizations here
  exit

  umount /mnt/run
  umount /mnt/sys
  umount /mnt/proc
  umount /mnt/dev
  umount /mnt
  ```

* Upload the raw image to S3:

  ```
  aws s3 cp ${IMAGE_ID}.raw s3://${BUCKET_NAME}/${IMAGE_ID}.raw
  ```

## Run `import-snapshot` operation

* Execute:

  ```
  aws ec2 import-snapshot --disk-container \
      "Description=CentOS,Format=RAW,UserBucket={S3Bucket=${BUCKET_NAME},S3Key=${IMAGE_ID}.raw}"
  ```

  This will return an ImportTaskId.  Set an environment variable to the
  ImportTaskId (substitute the example below with your task ID):

  ```
  TASK_ID=import-snap-087cd7311afba675f
  ```

* Wait for snapshot completion:

  Creating the snapshot will take several minutes.  You can check the status of
  the task by running:

  ```
  aws ec2 describe-import-snapshot-tasks --import-task-ids ${TASK_ID}
  ```

  While it is running, you will see output with a Status of **active**:

  ```
  {
      "ImportSnapshotTasks": [
          {
              "SnapshotTaskDetail": {
                  "Status": "active", 
                  "Format": "RAW", 
                  "DiskImageSize": 0.0, 
                  "UserBucket": {
                      "S3Bucket": "123456789012-vm-imports", 
                      "S3Key": "CentOS-8-ec2-8.1.1911-20200113.3.raw"
                  }, 
                  "Progress": "2", 
                  "StatusMessage": "pending"
              }, 
              "ImportTaskId": "import-snap-087cd7311afba675f"
          }
      ]
  }
  ```

  When it's complete, you'll see output with a Status of **completed**:

  ```
  {
      "ImportSnapshotTasks": [
          {
              "SnapshotTaskDetail": {
                  "Status": "completed", 
                  "SnapshotId": "snap-0fecb321718c3dcd9", 
                  "DiskImageSize": 10737418240.0, 
                  "UserBucket": {
                      "S3Bucket": "123456789012-vm-imports", 
                      "S3Key": "CentOS-8-ec2-8.1.1911-20200113.3.raw"
                  }, 
                  "Format": "RAW"
              }, 
              "ImportTaskId": "import-snap-087cd7311afba675f"
          }
      ]
  }
  ```

## Register an AMI

* Collect information about the snapshot that was created:

  ```
  # Substitute the snapshot ID using the output from the previous step
  SNAPSHOT_ID=snap-0fecb321718c3dcd9

  SNAPSHOT_SIZE=$(aws ec2 describe-snapshots --snapshot-ids ${SNAPSHOT_ID} --query Snapshots[].VolumeSize --output text)
  ```

* Register the AMI:

  ```
  aws ec2 register-image \
      --architecture x86_64 \
      --block-device-mappings "DeviceName=/dev/sda1,Ebs={DeleteOnTermination=true,SnapshotId=${SNAPSHOT_ID},VolumeSize=${SNAPSHOT_SIZE},VolumeType=gp2}" \
      --description "${IMAGE_DESCRIPTION}" \
      --ena-support \
      --name ${IMAGE_ID} \
      --root-device-name /dev/sda1 \
      --virtualization-type hvm
  ```

  The returned ImageId from the previous command can be used to launch EC2
  instances running CentOS.

## Cleanup

Clean up any unused resources (such as S3 buckets, EC2 instances, etc.) that
are no longer required.

## Links

* [Amazon documentation](https://docs.aws.amazon.com/vm-import/latest/userguide/vmimport-image-import.html)
* [RedHat documentation](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/deploying_red_hat_enterprise_linux_8_on_public_cloud_platforms/assembly_deploying-a-virtual-machine-on-aws_cloud-content)
* [Related CentOS forum posting](https://forums.centos.org/viewtopic.php?f=54&t=71951&start=10#p310689)

