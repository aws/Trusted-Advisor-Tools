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

#Create IAM role for lambda functions

resource "aws_iam_role" "ta-12Fnkpl8Y5-crossaccount-iam-role" {
  name = "ta-12Fnkpl8Y5-crossaccount-iam-role"

  assume_role_policy = jsonencode({
    Version: "2012-10-17",
    Statement: [
      {
        Effect: "Allow",
        Principal: {
          "AWS": [
            "arn:aws:sts::${var.main_aws_account_id}:assumed-role/ta-12Fnkpl8Y5-lambda-role/ta-12Fnkpl8Y5-deactivateiamkey",
            "arn:aws:sts::${var.main_aws_account_id}:assumed-role/ta-12Fnkpl8Y5-lambda-role/ta-12Fnkpl8Y5-cloudtraileventlookup"
          ]
        },
        Action: "sts:AssumeRole",
        Condition: {}
      }
    ]
  })

  inline_policy {
    name = "ta-12Fnkpl8Y5-lambda-permissions"
    policy = jsonencode({
      Version = "2012-10-17"
      Statement = [
        
        {
				"Sid": "Statement1",
				"Action": [
    				"iam:UpdateAccessKey"
				],
				"Effect": "Allow",
				"Resource": "*"
			  },
        {
        "Sid": "Statement2",
        "Action": [
            "cloudtrail:LookupEvents"
        ],
        "Effect": "Allow",
        "Resource": "*"
        },
        
      ]
    })
  }
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
      Version: "2012-10-17",
      Statement: [
        {
          Sid: "ActionsForResource",
          Effect: "Allow",
          Action: [
            "events:PutEvents"
          ],
          Resource: [
            "arn:aws:events:eu-west-1:${var.main_aws_account_id}:event-bus/ta-12Fnkpl8Y5-automation-event-bus"
          ]
        }
      ]
    })
  }
}


# Create EventBridge Rule
resource "aws_cloudwatch_event_rule" "ta-12Fnkpl8Y5-automation-event-rule" {
  name        = "ta-12Fnkpl8Y5-automation-event-rule"
  description = "Send TA event to main account"
  event_bus_name = "default"

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
  arn = "arn:aws:events:eu-west-1:${var.main_aws_account_id}:event-bus/ta-12Fnkpl8Y5-automation-event-bus"
  role_arn  = aws_iam_role.ta-12Fnkpl8Y5-events-role.arn
  event_bus_name = "default"
}

