# Web Redirector

```
aws cloudformation describe-stacks \
    --region us-east-1

aws cloudformation update-stack \
    --region us-east-1 \
    --stack-name WebRedirector \
    --template-body file://WebRedirector.yml \
    --parameters ParameterKey=HostedZoneName,ParameterValue=hostedzone.net ParameterKey=TargetZoneName,ParameterValue=targetzone.net \
    --capabilities CAPABILITY_NAMED_IAM
```
