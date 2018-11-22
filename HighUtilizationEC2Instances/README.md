
#Trusted Advisor Automation against High Utilization EC2 Instance

Trusted Advisor checks the Amazon Elastic Compute Cloud (Amazon EC2) instances that were running at any time during the last 14 days and alerts you if the daily CPU utilization was more than 90% on 4 or more days. Consistent high utilization can indicate optimized, steady performance, but it can also indicate that an application does not have enough resources. To get daily CPU utilization data, download the report for this check. These steps will go through the how to set up automated EC2 instance resize with approval. 

![alt txt](images/diagram.png)

## Walkthrough

### Step 0 - Preparing the EC2 instance.

<details>
<summary>**[ Click here for detailed steps ]**</summary><p>

1. From AWS console, take note of the region you are launching your resource .
2. Launch a vanilla EC2 instance with instance type **t2.nano** size. [Create EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/launching-instance.html "Create EC2 Instance")
	
	*( The OS and AMI does not really matter on this excersize, just ensure the instance can launch / stop / start successfully. )* 
	
3. The rest of the instance confguration can be kept default.

</p></details>


### Step 1 - Run Resize Automation Document.

<details>
<summary>**[ Click here for detailed steps ]**</summary><p>

1. From AWS console, click on Services and type in Systems Manager in the search bar and press enter. ![alt txt](images/step1.png)
2. Click on **Automation** on the left menu.
3. Click on **Execute automation**.
4. Search for **AWS-ResizeInstance** using the search bar.
5. Select on the document enter an **Instance Id** and the **Instance Type** you would like to change in the parameter, and click on **Execute automation**. ![alt txt](images/step5.png)
6. Watch the automation progress by clicking on **Automation** and the running with **AWS-ResizeInstance** document name. ![alt txt](images/step6.png)
7. You can also watch the EC2 instance being resized from the normal EC2 console. ![alt txt](images/step7.png)

</p></details>


### Step 2 - Building Resize Automation Document with Approval.

<details>
<summary>**[ Click here for detailed steps ]**</summary><p>

_**Note :**_

*Please create the SNS Topic below in the same region where you deployed the Automation Document and your instance on step 0. 
Please also take note of the region name for the remaining of the workshop.*


**SNS Topic**

1. Browse to AWS SNS console, click Services and type SNS and press enter.
2. From here click on **Create Topic**, type in **Topic Name** and **Display Name** and click **Create Topic**
3. Copy and paste the Topic ARN on a notepad ( we will use it later ).
4. Click on create subscription, select Email for protocol and type in your email addess on endpoint.
5. Click **Create subscription**.
6. You should receive an email from SNS to the **email address**, click on the verify link in the email to start accepting notification from this topic.

**Automation Document**

1. From AWS console, click on Services and type in Systems Manager in the search bar and press enter. ![alt txt](images/step1.png)
2. Click on **Documents** on the left menu.
3. Click on **Create Document**, type in the **name** and select **Automation document** for the **document type**.
4. Paste below into the content secton and replace the NotificationArn with the SNS topic ARN you took on step 3 above, then click **create document**

```
{
  "description": "Resize Instance with Approval",
  "assumeRole": "{{ AutomationAssumeRole }}",
  "schemaVersion": "0.3",
  "parameters": {
    "AutomationAssumeRole": {
      "default": "", 
      "description": "(Optional) The ARN of the role that allows Automation to perform the actions on your behalf.",
      "type": "String"
    },
    "InstanceId": {
      "description": "(Required) EC2 Instance to restart",
      "type": "String"
    },
    "InstanceType": {
      "description": "(Required) EC2 Instance Type",
      "type": "String"
    }
  },
  "mainSteps": [
    {
      "inputs": {
        "Message": "You have an Instance Resize approval request.",
        "NotificationArn": "<enter your SNS topic ARN here>",
        "MinRequiredApprovals": 1,
        "Approvers": [
          "<enter the arn of the IAM user who will be approving this, this can be your current user IAM role.>"
        ]
      },
      "name": "Approve",
      "action": "aws:approve",
      "onFailure": "Abort"
    },
    {
      "maxAttempts": 10,
      "inputs": {
        "RuntimeParameters": {
          "InstanceId": "{{ InstanceId }}",
          "InstanceType": "{{ InstanceType }}"
        },
        "DocumentName": "AWS-ResizeInstance"
      },
      "name": "Resize",
      "action": "aws:executeAutomation",
      "timeoutSeconds": 600,
      "onFailure": "Abort"
    }
  ]
}
```

**Execute automation document**

1. From AWS console, click on Services and type in Systems Manager in the search bar and press enter. 

![alt txt](images/step1.png)

2. Click on **Automation** on the left menu.
3. Click on **Execute automation**.
4. Search for the name of the Automation Document created above using the search bar.
5. Select on the document enter an **Instance Id** and the **Instance Type** you would like to change in the parameter, and click on **Execute automation**. ![alt txt](images/step5.png)
6. Watch the automation progress by clicking on **Automation** and the running with **AWS-ResizeInstance** document name. ![alt txt](images/step6.png)
8. Wait for an email from SNS notification asking for your approval, click on the approve url and select approve, and proceed with approving the request.
7. Watch EC2 instance being resized from the normal EC2 console. ![alt txt](images/step7.png)

</p></details>

### Step 3 Creating Lambda Function to trigger Automation Document.

**Note :**
The following steps must be deployed in **us-east-1** region.


<details>
<summary>**[ Click here for detailed steps ]**</summary><p>

1. From AWS console, click on Services and type in Lambda in the search bar and press enter. ![alt txt](images/step8.png)
2. Click on **Create Function** 
3. Type in your function name.
4. Set Runtime to **Python3.6**
5. Select Create custom role, click on **Edit**.
6. Choose Create a new IAM Role, and type in the role name.
7. Copy and paste below IAM Role and click **Allow**

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogStream",
                "logs:CreateLogGroup",
                "logs:PutLogEvents"
            ],
            "Resource": [
                "arn:aws:logs:*:*:*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "sns:Publish"
            ],
            "Resource": [
                "*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "iam:PassRole",
                "iam:CreateRole",
                "iam:DeleteRolePolicy",
                "iam:PutRolePolicy",
                "iam:GetRole",
                "iam:DeleteRole"
            ],
            "Resource": [
                "*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "ssm:StartAutomationExecution",
                "ssm:StopAutomationExecution",
                "ssm:GetAutomationExecution"
            ],
            "Resource": [
                "*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeInstances",
                "ec2:DescribeInstanceStatus",
                "ec2:StartInstances",
                "ec2:ModifyInstanceAttribute",
                "ec2:StopInstances"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "lambda:CreateFunction",
                "lambda:InvokeFunction",
                "lambda:AddPermission",
                "lambda:DeleteFunction",
                "lambda:GetFunction"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "cloudformation:CreateStack",
                "cloudformation:DeleteStack",
                "cloudformation:DescribeStacks"
            ],
            "Resource": "*"
        }
    ]
}
```


7. Copy Paste below Lambda Function Code and click **Save**

Lambda Function Code

![alt txt](images/step9.png)

```
import json
import boto3
import os

## EC2 Instance Table to decide which instance type to resize
i_list = {
  "t2":["nano","micro","small","medium","large","xlarge","2xlarge"],
  "t3":["nano","micro","small","medium","large","xlarge","2xlarge"],
  "m5d":["large","xlarge","2xlarge","4xlarge","12xlarge","24xlarge"],
  "m5":["large","xlarge","2xlarge","4xlarge","12xlarge","24xlarge"],
  "m4":["large","xlarge","2xlarge","4xlarge","10xlarge","16xlarge"],
  "c5d":["large","xlarge","2xlarge","4xlarge","9xlarge","18xlarge"],
  "c5":["large","xlarge","2xlarge","4xlarge","9xlarge","18xlarge"],
  "c4":["large","xlarge","2xlarge","4xlarge","8xlarge"],
  "f1":["2xlarge","16xlarge"],
  "g3":["4xlarge","8xlarge","16xlarge"],
  "g2":["2xlarge","8xlarge"],
  "p2":["xlarge","8xlarge","16xlarge"],
  "p3":["2xlarge","8xlarge","16xlarge"],
  "r5d":["large","xlarge","2xlarge","4xlarge","12xlarge","24xlarge"],
  "r5":["large","xlarge","2xlarge","4xlarge","12xlarge","24xlarge"],
  "r4":["large","xlarge","2xlarge","4xlarge","8xlarge","16xlarge"],
  "x1":["16xlarge","32xlarge"],
  "x1e":["xlarge","2xlarge","4xlarge","8xlarge","16xlarge","32xlarge"],
  "z1d":["large","xlarge","2xlarge","3xlarge","6xlarge","12xlarge"],
  "d2":["xlarge","2xlarge","4xlarge","8xlarge"],
  "i2":["xlarge","2xlarge","4xlarge","8xlarge"],
  "h1":["2xlarge","4xlarge","8xlarge","16xlarge"],
  "i3":["large","xlarge","2xlarge","4xlarge","8xlarge","16xlarge"]
}

## Function to decide new EC2 instance type
## This function will choose a higher instance type in the same family 
def getResize(IType):
    I = IType.split(".")
    Idx = i_list[I[0]].index(I[1])
    leng = len(i_list[I[0]]) - 1
    
    if Idx < leng:
        NIdx = Idx + 1
        RType = I[0] + "." + i_list[I[0]][NIdx]
    else:
        RType = "none"
    return(RType)

## Function to find instance type from instance id.
def getIType(IID,ec2):
    resp = ec2.describe_instances(InstanceIds=[IID])
    RType = resp['Reservations'][0]['Instances'][0]['InstanceType']
    return(RType)

## Lambda Handler Function
def lambda_handler(event, context):
    print(json.dumps(event))
    RARN = event['detail']['resource_id'].split(':')
    REGION = RARN[3]
    
    ssm = boto3.client('ssm', region_name=REGION)
    ec2 = boto3.client('ec2', region_name=REGION)
   
	 # Find Instance ID, check the type and decise which is the next instance type.
    IID = event['detail']['check-item-detail']['Instance ID']
    IType = getIType(IID,ec2)
    RType = getResize(IType)
    
    # Execute Automation Document of ResizeAutoDocument Environment variable.
    # xecute Automation Document
    if RType != "none":
        x = ssm.start_automation_execution(
                DocumentName = os.environ['ResizeAutoDocument'],
                Parameters= { 
                    'InstanceId': [IID], 
                    'InstanceType': [RType]
                  }
              )
        print(json.dumps(x))
        print("Executing Resize")
    else:
        print("No Higher Instance Found, Please Review other Instance Family")
    return(event)
```

7. Create environment variables with key **ResizeAutoDocument** and the name of the automation document you created on step 2 
![alt txt](images/step12.png)

7. Set the function timeout to 30 seconds or more.

8. You can test the lambda function with this payload to see if it triggers the automation document

```
{
  "detail": {
    "check-item-detail": {
      "Instance ID": "<replace with the instance id created in step 1>"
    },
	"resource_id":"arn:aws:ec2:<replace with the region>:xxxxxxx:instance/<enter the instance id created in step 1>"
  }
}
```

For visibility here is an example of the event being triggered by TA High Utilization Check.

```
{  
   "version":"0",
   "id":"4d04a964-88a6-7093-74c8-9af26598ca3e",
   "detail-type":"Trusted Advisor Check Item Refresh Notification",
   "source":"aws.trustedadvisor",
   "account":"000000000000",
   "time":"2018-11-20T01:01:49Z",
   "region":"us-east-1",
   "resources":[  

   ],
   "detail":{  
      "check-name":"High Utilization Amazon EC2 Instances",
      "check-item-detail":{  
         "Day 1":"98.8%",
         "Day 2":"98.8%",
         "Day 3":"98.8%",
         "Region/AZ":"us-west-2c",
         "14-Day Average CPU Utilization":"98.8%",
         "Day 14":"98.8%",
         "Day 13":"98.8%",
         "Day 12":"98.8%",
         "Day 11":"98.8%",
         "Day 10":"98.8%",
         "Instance Type":"m3.medium",
         "Instance ID":"i-b6218518",
         "Day 8":"98.8%",
         "Instance Name":"Overutilized4",
         "Day 9":"98.8%",
         "Number of Days over 90% CPU Utilization":"14",
         "Day 4":"98.8%",
         "Day 5":"98.8%",
         "Day 6":"98.8%",
         "Day 7":"98.8%"
      },
      "status":"WARN",
      "resource_id":"arn:aws:ec2:us-west-2:753667216438:instance/i-b6218518",
      "uuid":"e03b12af-004c-412b-9a76-c7d77a907c6d"
   }
}

```

</p></details>

### Step 4 Creating CloudWatch Events to trigger Lambda.

**Note :**
The following steps must be deployed in **us-east-1** region.

<details>
<summary>**[ Click here for detailed steps ]**</summary><p>

1. From AWS console, click on Services and type in CloudWatch in the search bar and press enter. ![alt txt](images/step10.png)
2. Click on **Rules** under Events on the left side of the menu screen.
3. Click **CreateRule**
4. Click **Edit** on the event source pattern and paste below.

```
{
  "detail-type": [
    "Trusted Advisor Check Item Refresh Notification"
  ],
  "source": [
    "aws.trustedadvisor"
  ],
  "detail": {
    "check-name": [
      "High Utilization Amazon EC2 Instances"
    ],
    "status": [
      "WARN"
    ]
  }
}
```

5. Click **Add target** 
6. Select Function you created on step 3.
7. Keep everything else default.
8. Click **Configure Details** 

**Mock Events**

Trusted Advisor won't trigger the event until a real EC2 instance has been detected on high util over 14 days, for the purpose of this event you can trigger a mock event by creating this rule below ( follow the same step above but change the Event Pattern to this.

```
{
  "detail-type": [
    "Trusted Advisor Check Item Refresh Notification"
  ],
  "source": [
    "awsmock.trustedadvisor"
  ],
  "detail": {
    "check-name": [
      "High Utilization Amazon EC2 Instances"
    ],
    "status": [
      "WARN"
    ]
  }
}
```

To trigger mock event run below command. ( Require AWS CLI )

`aws events put-events --entries file://mockpayload.json`

**mockpayload.json**

```
[
  {
    "DetailType": "Trusted Advisor Check Item Refresh Notification",
    "Source": "awsmock.trustedadvisor",
    "Time": "2017-02-07T00:55:52Z",
    "Resources": [],
    "Detail": "{\"check-name\":\"High Utilization Amazon EC2 Instances\",\"check-item-detail\":{\"Instance ID\":\"i-091db808edead90b6\"},\"status\":\"WARN\",\"resource_id\":\"arn:aws:ec2:ap-southeast-2:23232324324:instance/i-091db808edead90b6\"}"
  }
]

```
Adjust the time and instance Id then trigger the event


</p></details>


## CloudFormation Template

**Note:**

The following cloudformation stack needs to be deployed on us-east-1 only and it is meant to showcase the automation working ec2 resources in **us-east-1** only. To automate EC2 resources in other region than **us-east-1** you can create individual AutomationDocument with approval in each region with identical name, e.g: `Custom-TA-Resize-Approval` ( Follow Step 2 above ) and specify the name of the AutomationDocument in ResizeAutomationApprovalDocument parameter when launching the stack below 

<details>
<summary>**[ Click here for detailed steps ]**</summary><p>


1. Deploy CloudFormation stack using template `ta-automation-highutil-ec2.yml` in **us-east-1** region. Refer here for instructions on how to deploy Stack [Create Stack](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-console-create-stack.html "Create Stack")
2. If you are automating instance outside us-east-1 read the note above and fill in the AutomationDocument name you created in **ResizeAutomationApprovalDocument** parameter. If you leave them blank the automation will only works on **us-east-1**

</p></details>
