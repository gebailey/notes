# notes
Random notes and howtos

* [Building CentOS 7 and 8 AMIs](building-centos-ec2-amis/README.md)

  These steps detail how to build AMIs that can be started on AWS EC2 instances
  using cloud images provided by CentOS.

* [Flowroute SMS and MMS Message Forwarder](flowroute-message-forwarder/README.md)

  This CloudFormation template configures a HTTP API and Lambda function that
  can be used to receive SMS and MMS messages from a Flowroute DID and forward
  them to an arbitrary set of destination DIDs.

* [Web Redirector using API Gateway](web-redirector-api-gateway/README.md)

  Collection of CloudFormation resources to provision a Route53 hosted zone,
  certificate, CloudFront distribution, API Gateway, and a Lambda to return 301
  Redirect responses for any HTTP request.

  * Route53 is required to point apex domain to CloudFront
  * CloudFront is required to perform HTTP to HTTPS redirection
  * Redirect logic is implemented via API Gateway + Lambda

* [Web Redirector using CloudFront Function](web-redirector-cf-function/README.md)

  Collection of CloudFormation resources to provision a Route53 hosted zone,
  certificate, CloudFront distribution, and a CloudFront function to return 301
  Redirect responses for any HTTP request.

  * Route53 is required to point apex domain to CloudFront
  * CloudFront is required to perform HTTP to HTTPS redirection
  * Redirect logic is implemented via a CloudFront function
