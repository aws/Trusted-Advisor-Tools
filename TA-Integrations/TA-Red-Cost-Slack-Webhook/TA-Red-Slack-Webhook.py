############################################################
#Authors: Manas Satpathi & Sandeep Mohanty
#Company: AWS
#Date: June 20, 2022
############################################################

import boto3
import json
#import requests
import urllib.parse
import urllib.request

def lambda_handler(event, context):
   
   print(json.dumps(event))
   slack_webhook_url = event["SlackWebhookURL"]
   client = boto3.client('support', region_name='us-east-1')
   response = client.describe_trusted_advisor_checks(language='en')

   # Account number from STS get-caller-identity
   sts_client = boto3.client('sts', region_name='us-east-1')
   account_num = boto3.client('sts').get_caller_identity().get('Account')
   print (account_num)

   ##Number of elements returned
   num_checks = len(response["checks"])

   ##Create List of TA CheckIds
   checks = []
   #check_security_category = 0
   ta_checks_dict = {}
   for x in range(num_checks):
      checks.append(response["checks"][x]["id"])
      
      ##Store TA Checks in nested dict for cross referencing via TA check Id
      ta_checks_dict[response["checks"][x]["id"]] = {"name":response["checks"][x]["name"],"category":response["checks"][x]["category"]}
      #if (response["checks"][x]["category"] == "security"):
      # check_security_category += 1
      # print (check_security_category)
      # continue
   ##Get TA Check Summaries
   result = client.describe_trusted_advisor_check_summaries(checkIds=checks)

   count_ok = 0
   count_critical = 0
   count_warn = 0
   check_security_category = 0
   check_fault_tolerance_category = 0
   check_performance_category = 0
   check_cost_optimizing_category = 0
   check_service_limits_category = 0

   message = ""
   summary = ""

   for x in range(num_checks):
      check_status = result['summaries'][x]['status']
      check_id = result['summaries'][x]['checkId']
      #print(check_status)

      if(check_status == 'ok'):
        count_ok += 1
      elif(check_status == 'warning'):
        count_warn += 1
      elif(check_status == 'error'):
        count_critical += 1
        message += "HIGH RISK - " + "[" + str(ta_checks_dict[check_id]['category'])+ "] " + str(ta_checks_dict[check_id]['name']) + "\n"
        print (response["checks"][x])
        if (ta_checks_dict[check_id]['category'] == 'fault_tolerance'):
          check_fault_tolerance_category += 1
        if (ta_checks_dict[check_id]['category'] == 'security'):
          check_security_category += 1
        if (ta_checks_dict[check_id]['category'] == 'performance'):
          check_performance_category += 1
        if (ta_checks_dict[check_id]['category'] == 'cost_optimizing'):
          check_cost_optimizing_category += 1
        if (ta_checks_dict[check_id]['category'] == 'service_limits'):
          check_service_limits_category += 1
      else:
       continue

   check_category_dict = {"Security" : check_security_category, "Fault-Tolerance" : check_fault_tolerance_category, \
    "Performance" : check_performance_category, "Cost_optimizing" : check_cost_optimizing_category, \
    "Service_limits" : check_service_limits_category}

   summary += "\n=== Summary of TA High Risk (RED) Findings for "  + str (account_num) + " ===\n\n"

   summary += "Total High Risk (RED) Findings: " + str(count_critical) + " ("

   for i in range (len(check_category_dict.keys())):
    if list(check_category_dict.values())[i] > 0:
      summary += list(check_category_dict.keys())[i] + ": " + str(list(check_category_dict.values())[i]) + ", "

   summary = summary[:-2]
   check_estimatedMonthlySavings_total = 0
   num_checkIds = 0

   for x in range (len(result["summaries"])):
    try:
      check_estimatedMonthlySavings = result['summaries'][x]['categorySpecificSummary']['costOptimizing']['estimatedMonthlySavings']
      check_estimatedMonthlySavings_total += check_estimatedMonthlySavings
      num_checkIds += 1
    except KeyError:
        pass

   check_estimatedMonthlySavings_total = round(check_estimatedMonthlySavings_total * 100)/100
   
   print ("Total estiated monthly savings:", check_estimatedMonthlySavings_total)
   print ("No. of Checks:", num_checkIds)
   print ("Account No:", account_num)

   summary += ")\n"  
   summary += "Total Estimated Monthly Savings: $" + str(check_estimatedMonthlySavings_total) + ".\n\n"

   print("============= Post to Slack ===========")

   headers = {
      'Content-type': 'application/json'
   }

   data = "{content:" + '"' + summary + message + '"}'

   ## NOT USING Python "requests" library to avoid creating Lambda Layer in CloudFormation. Preserve CF portability
   #response = requests.post(slack_webhook_url, headers=headers, data=data)

   ## USING Python "urllib" instead

   data = data.encode('ascii')

   headers = {}
   headers['Content-Type'] = "application/json"

   ## Send the request
   print("URL = ", slack_webhook_url)
   req = urllib.request.Request(slack_webhook_url, data=data, headers=headers)
   resp = urllib.request.urlopen(req)

   ## Receive the response
   #respData = resp.read()
   #print("RESPONSE: ", respData)

   return {
     'statusCode': 200
   }

   ##############################

