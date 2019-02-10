AWS_PROFILE := baptiste
AWS_REGION  := eu-west-3

MAKEFILE_PATH     := $(abspath $(lastword $(MAKEFILE_LIST)))
CURRENT_DIRECTORY := $(patsubst %/,%,$(dir $(MAKEFILE_PATH)))

CLOUDFORMATION=aws cloudformation --profile ${AWS_PROFILE} --region ${AWS_REGION}
S3=aws s3 --profile ${AWS_PROFILE} --region ${AWS_REGION}
STACK_NAME=meetup-spot-instances

aws-console: ## Open the AWS Console
	xdg-open https://bgaillard.signin.aws.amazon.com/console

build-amis: ## Build the Mapper and Reducer AMIs
	sh build-amis.sh

cfn-create-stack: ## Create the Cloud Formation stack
cfn-create-stack: cfn-copy-templates
	${CLOUDFORMATION} create-stack --stack-name ${STACK_NAME} --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM --template-body file://${CURRENT_DIRECTORY}/cloudformation/root.yml
	${CLOUDFORMATION} wait stack-create-complete --stack-name ${STACK_NAME}

cfn-delete-stack: ## Delete the Cloud Formation stack
cfn-delete-stack:
	${CLOUDFORMATION} delete-stack --stack-name ${STACK_NAME}
	${CLOUDFORMATION} wait stack-delete-complete --stack-name ${STACK_NAME}

cfn-update-stack: ## Update the Cloud Formation stack
cfn-update-stack: cfn-copy-templates
	${CLOUDFORMATION} update-stack --stack-name ${STACK_NAME} --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM --template-body file://${CURRENT_DIRECTORY}/cloudformation/root.yml
	${CLOUDFORMATION} wait stack-update-complete --stack-name ${STACK_NAME}

cfn-copy-templates:
	${S3} cp cloudformation s3://meetup-spot-instances/cloudformation/ --recursive --include "*.yml"

demo1-push-documents: ## Push document SQS messages for the Demo1
	python demo1/push_documents.py --profile ${AWS_PROFILE} --region ${AWS_REGION}
demo1-start:
	python demo1/spot_requests_manager.py start --profile ${AWS_PROFILE} --region ${AWS_REGION} --app mapper --instance-count 3
	python demo1/spot_requests_manager.py start --profile ${AWS_PROFILE} --region ${AWS_REGION} --app reducer --instance-count 1
demo1-stop:
	python demo1/spot_requests_manager.py stop --profile ${AWS_PROFILE} --region ${AWS_REGION} --app mapper --instance-count 3
	python demo1/spot_requests_manager.py stop --profile ${AWS_PROFILE} --region ${AWS_REGION} --app reducer --instance-count 1

spot-instance-advisor: ## Open the Spot Instance Advisor page
	xdg-open https://aws.amazon.com/fr/ec2/spot/instance-advisor/

slide11-1: ## Print slide 11 first demo command
	@echo "aws ec2 describe-spot-price-history --profile ${AWS_PROFILE} --region ${AWS_REGION} --instance-type m5.large --product-description \"Linux/UNIX (Amazon VPC)\" --start-time 2019-02-06T09:00:00 --end-time 2019-02-06T15:00:00"

slide13-1: ## Print slide 13 first demo command
spot-requests:
	@echo "aws ec2 request-spot-instances --profile ${AWS_PROFILE} --region ${AWS_REGION} --instance-count 2 --spot-price 0.0041 --type "one-time" --launch-specification file://launch-specification.json"
slide13-2: ## Print slide 13 second demo command
	@echo "aws ec2 describe-spot-instance-requests --profile ${AWS_PROFILE} --region ${AWS_REGION}"
slide13-3: ## Print slide 13 third demo command
	@echo "aws ec2 cancel-spot-instance-requests --profile ${AWS_PROFILE} --region ${AWS_REGION} --spot-instance-request-ids id1 id2"
slide13-4: ## Print slide 13 fourth demon command
	@echo "aws ec2 terminate-instances --instance-ids id1 id2"

slides: ## Access to the slides
	xdg-open https://drive.google.com/open?id=1oTtDLlFi3TLONVghBCpIAwiofAT5m4HLU8qaMMTL_k0

.PHONY: aws-console slides

.DEFAULT_GOAL := help
help: Makefile
		@grep -E '(^[0-9a-zA-Z_-]+:.*?##.*$$)|(^##)' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[32m%-30s\033[0m %s\n", $$1, $$2}' | sed -e 's/\[32m##/[33m/'
