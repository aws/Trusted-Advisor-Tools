terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.67.0"
    }
  }
}

# Configure the AWS Provider
provider "aws" {
  region = var.region
  default_tags {
    tags = {
      project="ta-automation"
      ta_check_id="12Fnkpl8Y5"
      ta_check_name="Exposed Access Keys"
      deployment="terraform"
      auto-delete="no"
    }
  }
}

# Retrieve Organizations PrincipalOrgID
data "aws_organizations_organization" "org" {}

#Create IAM role for lambda functions

resource "aws_iam_role" "ta-12Fnkpl8Y5-lambda-role" {
  name = "ta-12Fnkpl8Y5-lambda-role"

  assume_role_policy = jsonencode({
    Version: "2012-10-17",
    Statement: [
      {
        Action: "sts:AssumeRole",
        Principal: {
          Service: "lambda.amazonaws.com"
        },
        Effect: "Allow",
        Sid: ""
      }
    ]
  })

  inline_policy {
    name = "ta-12Fnkpl8Y5-lambda-permissions"
    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          Sid: "Statement1"
          Action = [
            "logs:CreateLogGroup",
            "logs:CreateLogStream",
            "logs:PutLogEvents"
          ],
          Effect   = "Allow"
          Resource = "arn:aws:logs:*:*:*"
        },
        {
				  Sid: "Statement2",
				  Action: [
    				"iam:UpdateAccessKey"
				  ],
				  Effect: "Allow",
				  Resource: "*"
			  },
        {
          Sid: "Statement3",
          Action: [
            "cloudtrail:LookupEvents"
          ],
          Effect: "Allow",
          Resource: "*"
        },
        {
          Sid: "Statement4",
          Action: [
            "sns:Publish"
          ],
          Effect: "Allow",
          Resource: aws_sns_topic.ta-12Fnkpl8Y5-exposedkey-snstopic.arn
        },
        {
          Sid: "Statement5",
          Action: [
            "sts:AssumeRole"
          ],
          Effect: "Allow",
          Resource: "arn:aws:iam::*:role/ta-12Fnkpl8Y5-crossaccount-iam-role"
        } 
      ]
    })
  }
}

#Create IAM role for Step Functions
resource "aws_iam_role" "ta-12Fnkpl8Y5-stepfunctions-role" {
  name = "ta-12Fnkpl8Y5-stepfunctions-role"

  assume_role_policy = jsonencode({
    Version: "2012-10-17",
    Statement: [
      {
        Action: "sts:AssumeRole",
        Principal: {
          Service: "states.amazonaws.com"
        },
        Effect: "Allow",
        Sid: ""
      }
    ]
  })

  inline_policy {
    name = "ta-12Fnkpl8Y5-stepfunctions-permissions"
    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          Sid: "Statement1"
          Action   = [
                 "lambda:InvokeFunction"
             ],
          Effect   = "Allow"
          Resource = "*"
        }
      ]
    })
  }
}

# Create zip file for Lambda function

data "archive_file" "python_lambda_package" {  
  type = "zip"  
  source_file = "${path.module}/src/ta-12Fnkpl8Y5-deactivateiamkey.py" 
  output_path = "ta-12Fnkpl8Y5-deactivateiamkey.zip"
}

# Create Lambda function to Deactivate IAM Access Key

resource "aws_lambda_function" "ta-12Fnkpl8Y5-deactivateiamkey" {

  function_name = "ta-12Fnkpl8Y5-deactivateiamkey"
  filename      = "ta-12Fnkpl8Y5-deactivateiamkey.zip"
  source_code_hash = data.archive_file.python_lambda_package.output_base64sha256
  role          = aws_iam_role.ta-12Fnkpl8Y5-lambda-role.arn
  description   = "TA Automation: Deactivate IAM Access Key"
  handler       = "ta-12Fnkpl8Y5-deactivateiamkey.lambda_handler"
  architectures = ["arm64"]
  runtime       = "python3.11"
  timeout       = 10
  
  tags = {
    Name = "ta-12Fnkpl8Y5-deactivateiamkey"
  }
}

# Create zip file for Lambda function

data "archive_file" "ta-12Fnkpl8Y5-cloudtraileventlookup_package" {  
  type = "zip"  
  source_file = "${path.module}/src/ta-12Fnkpl8Y5-cloudtraileventlookup.py" 
  output_path = "ta-12Fnkpl8Y5-cloudtraileventlookup.zip"
}

# Create Lambda function to lookup Cloudtrail events

resource "aws_lambda_function" "ta-12Fnkpl8Y5-cloudtraileventlookup" {

  function_name = "ta-12Fnkpl8Y5-cloudtraileventlookup"
  filename      = "ta-12Fnkpl8Y5-cloudtraileventlookup.zip"
  source_code_hash = data.archive_file.ta-12Fnkpl8Y5-cloudtraileventlookup_package.output_base64sha256
  role          = aws_iam_role.ta-12Fnkpl8Y5-lambda-role.arn
  description   = "TA Automation: Exposed key lookup Cloudtrail events"
  handler       = "ta-12Fnkpl8Y5-cloudtraileventlookup.lambda_handler"
  architectures = ["arm64"]
  runtime       = "python3.11"
  timeout       = 10

  tags = {
    Name = "ta-12Fnkpl8Y5-cloudtraileventlookup"
  }
}

# Create SNS Topic

resource "aws_sns_topic" "ta-12Fnkpl8Y5-exposedkey-snstopic" {
  name = "ta-12Fnkpl8Y5-exposedkey-snstopic"
  kms_master_key_id = "alias/aws/sns"
}

# Create SNS Topic Subscription

resource "aws_sns_topic_subscription" "ta-12Fnkpl8Y5-exposedkey-email" {
  topic_arn = aws_sns_topic.ta-12Fnkpl8Y5-exposedkey-snstopic.arn
  protocol = "email"
  endpoint = var.email
}

# Create zip file for Lambda function

data "archive_file" "ta-12Fnkpl8Y5-snsmessage_package" {  
  type = "zip"  
  source_file = "${path.module}/src/ta-12Fnkpl8Y5-snsmessage.py" 
  output_path = "ta-12Fnkpl8Y5-snsmessage.zip"
}

# Create Lambda function to send SNS message

resource "aws_lambda_function" "ta-12Fnkpl8Y5-snsmessage" {

  function_name = "ta-12Fnkpl8Y5-snsmessage"
  filename      = "ta-12Fnkpl8Y5-snsmessage.zip"
  source_code_hash = data.archive_file.ta-12Fnkpl8Y5-snsmessage_package.output_base64sha256
  role          = aws_iam_role.ta-12Fnkpl8Y5-lambda-role.arn
  description   = "TA Automation: Send Exposed Key Email Notification"
  handler       = "ta-12Fnkpl8Y5-snsmessage.lambda_handler"
  architectures = ["arm64"]
  runtime       = "python3.11"
  timeout       = 10

  environment {
    variables = {
      "TOPIC_ARN" = aws_sns_topic.ta-12Fnkpl8Y5-exposedkey-snstopic.arn
    }
  }

  tags = {
    Name = "ta-12Fnkpl8Y5-snsmessage"
  }
}

# Create Step Function

resource "aws_sfn_state_machine" "ta-12Fnkpl8Y5-automation_sfn_state_machine" {
  name     = "ta-12Fnkpl8Y5-automation"
  role_arn = aws_iam_role.ta-12Fnkpl8Y5-stepfunctions-role.arn

  definition = jsonencode({
    Comment = "A state machine that executes multiple Lambda functions in sequence"
    StartAt = "LambdaFunction1"
    States = {
      LambdaFunction1 = {
        Type     = "Task"
        Resource = aws_lambda_function.ta-12Fnkpl8Y5-deactivateiamkey.arn
        Next     = "LambdaFunction2"
      },
      LambdaFunction2 = {
        Type     = "Task"
        Resource = aws_lambda_function.ta-12Fnkpl8Y5-cloudtraileventlookup.arn
        Next     = "LambdaFunction3"
      },
      LambdaFunction3 = {
        Type     = "Task"
        Resource = aws_lambda_function.ta-12Fnkpl8Y5-snsmessage.arn
        End      = true
      }
    }
  })
}


#Create IAM Role for Eventbridge rule
resource "aws_iam_role" "ta-12Fnkpl8Y5-events-role" {
  name = "ta-12Fnkpl8Y5-events-role"

  assume_role_policy = jsonencode({
    Version: "2012-10-17",
    Statement: [
      {
        Action: "sts:AssumeRole",
        Principal: {
          Service: "events.amazonaws.com"
        },
        Effect: "Allow",
        Sid: ""
      }
    ]
  })

  inline_policy {
    name = "ta-12Fnkpl8Y5-events-permissions"
    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [
        {
          Sid: "Statement1"
          Action   = [
                 "states:StartExecution"
             ],
          Effect   = "Allow"
          Resource = aws_sfn_state_machine.ta-12Fnkpl8Y5-automation_sfn_state_machine.arn
        }
      ]
    })
  }
}

# Create EventBridge Bus

resource "aws_cloudwatch_event_bus" "ta-12Fnkpl8Y5-automation-event-bus" {
  name = "ta-12Fnkpl8Y5-automation-event-bus"
}


# Create EventBridge Bus Policy

resource "aws_cloudwatch_event_bus_policy" "test" {
  policy         = jsonencode({
    Version: "2012-10-17",
    Statement: [
    {
      Sid: "AllowAllAccountsFromOrganizationToPutEvents",
      Effect: "Allow",
      Principal: "*",
      Action: "events:PutEvents",
      Resource: aws_cloudwatch_event_bus.ta-12Fnkpl8Y5-automation-event-bus.arn,
      Condition: {
        StringEquals: {
          "aws:PrincipalOrgID": data.aws_organizations_organization.org.id
        }
      }
    }
    ]
  })
  event_bus_name = aws_cloudwatch_event_bus.ta-12Fnkpl8Y5-automation-event-bus.name
  
}


# Create EventBridge Rule
resource "aws_cloudwatch_event_rule" "ta-12Fnkpl8Y5-automation-event-rule" {
  name        = "ta-12Fnkpl8Y5-automation-event-rule"
  description = "Trigger Step Function execution"
  event_bus_name = aws_cloudwatch_event_bus.ta-12Fnkpl8Y5-automation-event-bus.name

  event_pattern = jsonencode({
    detail: {
    check-name: ["Exposed Access Keys"]
    },
    detail-type: ["Trusted Advisor Check Item Refresh Notification"],
    source: ["aws.trustedadvisor"]
  })
}

# New EventBridge Target resource
resource "aws_cloudwatch_event_target" "step_function_target" {
  rule        = aws_cloudwatch_event_rule.ta-12Fnkpl8Y5-automation-event-rule.name
  target_id  = "ExecuteStepFunction"
  arn = aws_sfn_state_machine.ta-12Fnkpl8Y5-automation_sfn_state_machine.arn
  role_arn  = aws_iam_role.ta-12Fnkpl8Y5-events-role.arn
  event_bus_name = aws_cloudwatch_event_bus.ta-12Fnkpl8Y5-automation-event-bus.name

}

# Send Eventbridge bus arn to output
output "event_bus_arn" {
  value = aws_cloudwatch_event_bus.ta-12Fnkpl8Y5-automation-event-bus.arn
}