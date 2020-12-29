# Flowroute Message Forwarder

This CloudFormation template configures a HTTP API and Lambda function that can
be used to receive SMS and MMS messages from a Flowroute DID and forward them
to an arbitrary set of destination DIDs.

The initial use case was to handle the scenario where friends would
inadvertently send text messages to a home phone line that didn't handle it;
once the home phone line was ported to a VoIP system (using Flowroute as the
provider), it became possible to configure such a system to forward the SMS and
MMS messages to one or more cell numbers.

### Prerequisites

* An AWS account
* Familiarity with AWS services and the AWS CLI
* A Flowroute account with a provisioned DID
* A Flowroute API key

### CloudFormation

The following command will create the `FlowrouteMessageForwarder` stack with
all of the AWS resources in it:

```bash
aws cloudformation create-stack \
    --stack-name FlowrouteMessageForwarder \
    --template-body file://FlowrouteMessageForwarder.yml \
    --capabilities CAPABILITY_NAMED_IAM
```

The `CAPABILITY_NAMED_IAM` capability is required because the CloudFormation
stack creates an IAM role that's used by the Lambda function.

### Parameter Store Configuration

Navigate to the [API
Control](https://manage.flowroute.com/accounts/preferences/api/) page on the
Flowroute web site, and use the "Access Key" and "Secret Key" at the bottom of
the page for the following parameter store values:

| Parameter Name | Sample Value | Description
| -------------- | ------------ | -----------
| `flowroute_messages_bucket` | `flowroute-messages-123456789012` | S3 bucket (Created automatically by CloudFormation)
| `flowroute_number_map` | `{"14805551111": ["16025552222", "16025553333"]}` | Mapping of source to destination DIDs (JSON format)
| `flowroute_access_key` | `12345678` | Flowroute API Access Key (approx 8 numbers)
| `flowroute_secret_key` | `########` | Flowroute API Secret Key (approx 32 chars)

In the configuration above, messages arriving on the `14805551111` DID will be
forwarded to both `16025552222` and `16025553333`.  Additional keys can be
added if you own multiple DIDs; each DID you own will need its own list of
destination DIDs.

These can be set either via the AWS console or via the AWS CLI using the
following commands:

```bash
aws ssm put-parameter --type SecureString --name flowroute_number_map --value '{"14805551111": ["16025552222", "16025553333"]}'
aws ssm put-parameter --type SecureString --name flowroute_access_key --value access-key-goes-here
aws ssm put-parameter --type SecureString --name flowroute_secret_key --value secret-key-goes-here
```

### Lambda Update

The CloudFormation template creates a stub function; use the following command
to upload the message processor Lambda code (with the bundled requests
library):

```bash
./update_lambda.sh
```

### Flowroute Configuration

Retrieve the generated API endpoint from the CloudFormation stack using:

```bash
aws cloudformation describe-stacks \
    --stack-name FlowrouteMessageForwarder \
    --query Stacks[].Outputs[].OutputValue \
    --output text
```

Navigate to the [API
Control](https://manage.flowroute.com/accounts/preferences/api/) page on the
Flowroute web site, and set the SMS and MMS Webhook values to the URL output by
the previous command.
