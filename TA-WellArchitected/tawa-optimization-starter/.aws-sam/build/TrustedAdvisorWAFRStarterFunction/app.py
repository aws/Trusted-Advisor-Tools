import boto3
import json
import uuid
import time
import requests
from bs4 import BeautifulSoup


################################################################################################################
# Find all resources name and arn with matching tags
################################################################################################################
def get_workload_resources(workloadtag):

    try:
        resources = {"resource_arns":[], "resource_names":[]}
        resource_group_client_workload_account = boto3.client('resourcegroupstaggingapi')
        paginator = resource_group_client_workload_account.get_paginator('get_resources')
        response_iterator = paginator.paginate(TagFilters=[
                    {
                        'Key': workloadtag['TagKey'],
                        'Values': [ workloadtag['TagValue'] ]
                    },
                ])
        for page in response_iterator:
            for resource in page['ResourceTagMappingList']:
                resources["resource_arns"].append(resource['ResourceARN'])
                resources["resource_names"].append(resource['ResourceARN'].split(':')[-1])
    except Exception as e:
        print(e)
        resources = {"resource_arns":[], "resource_names":[]}
    return resources


################################################################################################################
# Generate a baseline Trusted Advisor Mapping with AWS Well-Architected Best Practices.
# WARNING This Function takes 60 mins to generate the mapping and it will create a temporary WA Tool Workload.
################################################################################################################
def gather_wellarchitected_ta_mapping():
    try:
        client = boto3.client('wellarchitected', region_name='us-east-1')
        tempworkloaduuid = uuid.uuid4()
        
        workload = client.create_workload(
            WorkloadName='watemp-' + str(tempworkloaduuid),
            Description='This is a temporary workload to get TA Mapping, it will/should be deleted after mapping is captured',
            Environment= 'PREPRODUCTION',
            Lenses=['wellarchitected'],
            NonAwsRegions= ['watemp'],
            ReviewOwner= 'watemp',
            DiscoveryConfig={
                'TrustedAdvisorIntegrationStatus': 'ENABLED',
                'WorkloadResourceDefinition': [ 'WORKLOAD_METADATA' ]
                }
            )
        workloadobj = client.get_workload(
            WorkloadId=workload['WorkloadId']
            )
            
        lensobj= client.get_lens(LensAlias=workloadobj['Workload']['Lenses'][0])
        workdetails = {
            'WorkloadId': workloadobj['Workload']['WorkloadId'],
            'WorkloadArn': workloadobj['Workload']['WorkloadArn'],
            'Pillars': workloadobj['Workload']['PillarPriorities'],
            'LensAlias': workloadobj['Workload']['Lenses'][0],
            'LensArn': lensobj['Lens']['LensArn']
        }
        tamapping = []
        categories = []
        answersres = client.list_answers(
            WorkloadId=workdetails['WorkloadId'],
            LensAlias=workdetails['LensAlias'],
        )
        for i in answersres['AnswerSummaries']:
            categories.append(clean_answers(i))
        
        while 'NextToken' in answersres:
            answersres = client.list_answers(
                WorkloadId=workdetails['WorkloadId'],
                LensAlias=workdetails['LensAlias'],
                NextToken=answersres['NextToken']
            )
            
            for i in answersres['AnswerSummaries']:
                categories.append(clean_answers(i))
    
        print("Waiting For TA Check to populate in WA Tool")    
        time.sleep(30)
        
        print("Compiling TA Checks")
        for categitem in categories:
            bpitemlist = []
            for bpitem in categitem['Choices']:
                
                bp_risk = get_bp_level_risk(bpitem['ChoiceId'],categitem['PillarId'])
                
                checkres = client.list_check_details(
                    WorkloadId=workdetails['WorkloadId'],
                    LensArn=workdetails['LensArn'],
                    PillarId=categitem['PillarId'],
                    QuestionId=categitem['QuestionId'],
                    ChoiceId=bpitem['ChoiceId']
                )
                tachecks = []
                for check in checkres['CheckDetails']:
                    clean_check(check)
                    tachecks.append(check)
                bptaitem = {
                    'BestPracticeId' : bpitem['ChoiceId'],
                    'BestPracticeTitle' : bpitem['Title'],
                    'BestPracticeDesc' : bpitem['Description'],
                    'BestPracticeRisk' : bp_risk,
                    'TrustedAdvisorChecks' : tachecks
                }
                bpitemlist.append(bptaitem)
                while 'NextToken' in checkres:
                    checkres = client.list_check_details(
                        WorkloadId=workdetails['WorkloadId'],
                        LensArn=workdetails['LensArn'],
                        PillarId=categitem['PillarId'],
                        QuestionId=categitem['QuestionId'],
                        ChoiceId=bpitem['ChoiceId'],
                        NextToken=checkres['NextToken']
                    )
                    tachecks = []
                    for check in checkres['CheckDetails']:
                        clean_check(check)
                        tachecks.append(check)
                    bptaitem = {
                        'BestPracticeId' : bpitem['ChoiceId'],
                        'BestPracticeTitle' : bpitem['Title'],
                        'BestPracticeDesc' : bpitem['Description'],
                        'BestPracticeRisk' : bp_risk,
                        'TrustedAdvisorChecks' : tachecks
                    }
                    bpitemlist.append(bptaitem)
            categitem['Choices'] = bpitemlist
            
        client.delete_workload(
            WorkloadId=workdetails['WorkloadId']
            )
            
        for question in categories:
            for bp in question['Choices']:
                if len(bp['TrustedAdvisorChecks']) > 0:
                    for tacheck in bp['TrustedAdvisorChecks']:
                        check = {
                            "TrustedAdvisorCheckId" : tacheck['Id'],
                            "TrustedAdvisorCheckName" : tacheck['Name'],
                            "TrustedAdvisorCheckDesc" : tacheck['Description'],
                            "WAPillarId": tacheck['PillarId'],
                            "WAQuestionId": tacheck['QuestionId'],                        
                            "WABestPracticeId" : tacheck['ChoiceId'],
                            "WABestPracticeTitle" : bp['BestPracticeTitle'],
                            "WABestPracticeDesc" : bp['BestPracticeDesc'],
                            "WABestPracticeRisk" : bp['BestPracticeRisk']
                        }
                        tamapping.append(check)
                        
    except Exception as e:
        print(e)

    return tamapping


################################################################################################################
# Gather all Trusted Advisor Checks Flagged Resources ( given matching arn / names ) 
################################################################################################################
def get_trusted_advisor_resources(checkid, workload_resources = None):
    try:
        client = boto3.client('support', region_name='us-east-1')
        tacheckres = client.describe_trusted_advisor_check_result(
            checkId=checkid,
            language='en'
            )
        flagged_resources = []
        if 'flaggedResources' in tacheckres['result']:
        
            if workload_resources != None:
                
                for res in tacheckres['result']['flaggedResources']:
                    if 'metadata'in res:
                        if res['status'] in ['ok','warning', 'error'] and any(x in res['metadata'] for x in workload_resources['resource_arns']):
                            #resource_index = get_index_value(res['metadata'], workload_resources['resource_arns'])
                            #flagged_resources.append(workload_resources['resource_arns'][resource_index])                        
                            flagged_resources.append(res)
                        elif res['status'] in ['ok','warning', 'error'] and any(x in res['metadata'] for x in workload_resources['resource_names']):
                            #resource_index = get_index_value(res['metadata'], workload_resources['resource_names'])
                            #flagged_resources.append(workload_resources['resource_names'][resource_index])  
                            flagged_resources.append(res)
                    else:
                        flagged_resources.append(res)
            else:
                flagged_resources=tacheckres['result']['flaggedResources']
    except Exception as e:
        print(e)
        
    return flagged_resources

################################################################################################################
# Generate a list of trusted advisor checks with detected flagged resources
################################################################################################################
def get_wa_check_results(workload_resources = None):
    try:
        wa_check_results = []
        if workload_resources is not None:
            wata_list = gather_wellarchitected_ta_mapping()
            wata_results = []
            for wata in wata_list:
                wata_res = wata
                wata_res['FlaggedResources']=get_trusted_advisor_resources(wata['TrustedAdvisorCheckId'], workload_resources)
                wata_results.append(wata_res)
        else:
            wata_list = gather_wellarchitected_ta_mapping()
            wata_results = []
            for wata in wata_list:
                wata_res = wata
                wata_res['FlaggedResources']=get_trusted_advisor_resources(wata['TrustedAdvisorCheckId'])
                wata_results.append(wata_res)
        for x in wata_results:
            if len(x["FlaggedResources"]) != 0:
                wa_check_results.append(x)
    except Exception as e :
        print(e)
                
    return(wa_check_results)

################################################################################################################
# Generate HTML Page
################################################################################################################
def json_to_html(data):
    try:
        
        style = '''
        
        .styled-table {
            border-collapse: collapse;
            margin: 25px 0;
            font-size: 0.9em;
            font-family: sans-serif;
            min-width: 400px;
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.15);
            border: 1px solid black;
        }
        .styled-table thead tr {
            background-color: #009879;
            color: #ffffff;
            text-align: left;
            border: 1px solid black;
        }
        .styled-table th,
        .styled-table td {
            padding: 12px 15px;
            border: 1px solid black;
        }
        .styled-table tbody tr {
            border-bottom: 1px solid #dddddd;
            border: 1px solid black;
        }
        
        .styled-table tbody tr:nth-of-type(even) {
            background-color: #f3f3f3;
            border: 1px solid black;
        }
        
        .styled-table tbody tr:last-of-type {
            border-bottom: 2px solid #009879;
            border: 1px solid black;
        }
        .styled-table tbody tr.active-row {
            font-weight: bold;
            color: #009879;
            border: 1px solid black;
        }
        
        '''
        
        html = "<html><head><style>" + style + "</style></head><body>"
        html += "<table class='styled-table'>"
        html += "<tr>"
        html += "<td width='10%'><h4>Name</h4></td>"
        html += "<td width='40%'><h4>Description</h4></td>"
        html += "<td width='15%'><h4>Best Practice</h4></td>"
        html += "<td width='5%'><h4>Pillar</h4></td>"
        html += "<td width='5%'><h4>Business Risk</h4></td>"
        html += "<td width='5%'><h4>Status</h4></td>"
        html += "<td width='5%'><h4>Identifier</h4></td>"
        html += "<td width='5%'><h4>Region</h4></td>"        
        html += "</tr>"
        for i in data:
            fr = i["FlaggedResources"]
            for r in fr:
                if 'region' in r:
                    region = r['region']
                else:
                    region = "N/A"
                if 'resourceId' in r:
                    resid = r['resourceId']
                else:
                    resid = "N/A"                
                if 'metadata' in r:
                    name = r['metadata'][1]
                else:
                    name = "N/A"     
                if 'status' in r:
                    status = r['status']
                else:
                    status = "N/A"   
                pillar_url_path =  get_pillar_path(i["WAPillarId"])
                
                html += "<tr>"
                html += "<td>" + i["TrustedAdvisorCheckName"] + "</td>"
                html += "<td>" + i["TrustedAdvisorCheckDesc"] + "</td>"
                html += "<td>"
                html += "<a href=https://docs.aws.amazon.com/wellarchitected/latest/"+ pillar_url_path + "/" + i["WABestPracticeId"] + ".html" + ">" + i["WABestPracticeTitle"] + "</a>"
                html += "<br><br>" + i["WABestPracticeDesc"]
                html += "</td>"
                html += "<td>" + i["WAPillarId"] + "</td>"            
                html += "<td>" + i["WABestPracticeRisk"] + "</td>"
                html += "<td>" + status + "</td>"
                html += "<td>" + name + "</td>"
                html += "<td>" + region + "</td>"
                html += "</tr>"
        html += "</table>"
        html += "</body></html>"
    except Exception as e:
        print(e)
        
    return(html)

def getdata(url):
    try:
        r = requests.get(url) 
    except Exception as e:
        print(e)
    return r.text 

def get_pillar_path(pillarid):
    try:

        pillar_url_path = "None"
        
        if pillarid == "costOptimization":
            pillar_url_path = "cost-optimization-pillar"
        elif pillarid == "security":
            pillar_url_path = "security-pillar"
        elif pillarid == "reliability":
            pillar_url_path = "reliability-pillar"
        elif pillarid == "operationalExcellence":
            pillar_url_path = "operational-excellence-pillar"
        elif pillarid == "performance":
            pillar_url_path = "performance-efficiency-pillar"
        elif pillarid == "sustainability":
            pillar_url_path = "sustainability-pillar"
    except Exception as e:
        print(e)
        
    return(pillar_url_path)
    
def get_bp_level_risk(bpid,pillarid):
    result = "N/A"
    try:
        pillar_url_path = get_pillar_path(pillarid)
        texts = []
        htmldata = getdata("https://docs.aws.amazon.com/wellarchitected/latest/"+ pillar_url_path  +"/" + bpid + ".html") 
        soup = BeautifulSoup(htmldata, 'html.parser') 
        for data in soup.find_all("p"): 
             texts.append(data.get_text())
        for t in texts:
            if "Level of risk exposed if this best" in t:
                x = t.split(":")
                result =x[1].strip()
                break
    except Exception as e:
        print(e)
    return(result)
        
def put_links_to_workload(workload_data,wa_check_results,report_file_path):
    try:
        client = boto3.client('wellarchitected', region_name=workload_data['region'])
        workloadobj = client.create_workload(
            WorkloadName=workload_data['name'],
            Description='This is a workload to run the review',
            Environment= 'PREPRODUCTION',
            Lenses=['wellarchitected'],
            AwsRegions= [workload_data['region']],
            ReviewOwner= workload_data['owner'],
            DiscoveryConfig={
                'TrustedAdvisorIntegrationStatus': 'ENABLED',
                'WorkloadResourceDefinition': [ 'WORKLOAD_METADATA' ]
                },
            Tags={
                workload_data['tagkey']: workload_data['tagvalue']
            },            
            )
        for chk in wa_check_results:
            client.update_answer(
                WorkloadId=workloadobj['WorkloadId'],
                LensAlias='wellarchitected',
                QuestionId=chk['WAQuestionId'],
                Notes=report_file_path
            )
    except Exception as e:
        print(e)
        
        
####################
# Utility functions
####################
def clean_check(check):
    try:
        del check['Status']
        del check['LensArn']
        del check['AccountId']
        del check['FlaggedResources']
        del check['UpdatedAt']
        del check['Provider']
    except Exception as e:
        print(e)
    return check
def clean_answers(answers):
    try:
        del answers['SelectedChoices']
        del answers['ChoiceAnswerSummaries']
        del answers['IsApplicable']        
        choices = answers['Choices']
        cleaned_choices = []
        for i in choices:
            cleaned_choices.append(clean_choice(i))
        answers['Choices']= cleaned_choices
    except Exception as e:
        print(e)
    return answers
def clean_choice(choices):
    return choices
def get_index_value(metadata_list, workload_resources_list):
    for index, resource in enumerate(workload_resources_list):
        if resource in metadata_list:
            return index
def write_to_s3(wa_check_results, bucket, folder , workloadname ):
    html_output = json_to_html(wa_check_results)
    json_output = wa_check_results
    s3 = boto3.resource('s3')
    reportname = workloadname + '-' + str(uuid.uuid4())
    
    ###WRITE HTML RAW DATA
    html_s3key = folder + '/' + str(reportname) + '.html'
    object = s3.Object(
        bucket_name=bucket, 
        key=html_s3key
    )
    object.put(Body=html_output)
    
    ###WRITE JSON RAW DATA
    json_s3key = folder + '/json/' + str(reportname) + '.json'
    object = s3.Object(
        bucket_name=bucket, 
        key=json_s3key
    )
    object.put(Body=json.dumps(json_output))
    
    return(html_s3key)

def send_signal(execid, signal):
    try:
        client = boto3.client('ssm')
        client.send_automation_signal(
        AutomationExecutionId=execid,
        SignalType=signal
        )
    except Exception as e:
        print(e)


def send_report_sns(reporttopicarn,report_link):
    try:
        client = boto3.client('sns')
        client.publish(
            TopicArn=reporttopicarn,
            Message=report_link,
            Subject='Trusted Advisor WAFR Report URL',
        )
    except Exception as e:
        print(e)


def lambda_handler(event, context):

    try:

        tagkey = event['Parameters']['ResourceTagKey']
        tagvalue = event['Parameters']['ResourceTagValue']
        bucket = event['Parameters']['TrustedAdvisorReportingBucket']
        folder = 'report'
        websiteurl = event['Parameters']['TrustedAdvisorReportingHost']
        workloadname = event['Parameters']['BestPracticeReviewName']
        workloadregion = event['Parameters']['BestPracticeReviewRegion']
        workloadowner = event['Parameters']['BestPracticeReviewOwner']
        reporttopicarn = event['Parameters']['ReportEventTopicArn']
    
        
    
        workload_data = {
            'name' : workloadname,
            'region': workloadregion,
            'owner' : workloadowner,
            'tagkey' : tagkey,
            'tagvalue' :tagvalue
        }
        
        workload_tags = {
            'TagKey' : tagkey,
            'TagValue': tagvalue
        }

        if tagkey == 'None' or tagvalue == 'None':
            res = None
        else:
            print("Gathering resources with tags ... ")
            res = get_workload_resources(workload_tags)
        
        print("Compiling Trusted Advisor Well-Architected check results ...")  
        wa_check_results = get_wa_check_results(res)
    
        print("Composing report & placing it into bucket ... ")
        report_file_path = write_to_s3(wa_check_results,bucket,folder,workloadname)
        report_link = websiteurl + '/'  + report_file_path
    
        print("Putting report links into Well-Architected Tool notes ...")
        put_links_to_workload(workload_data,wa_check_results,report_link)

        send_signal(event['AutomationExecutionId'],'Approve' )

        send_report_sns(reporttopicarn,report_link)

        result_output = {
            "statusCode": 200,
            "body": json.dumps({
                "message": report_link
            }),
        }

        return result_output

    except Exception as e :
        print(e)
        
        result_output = {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Oops Something went wrong"
            }),
        }
        
        send_signal(event['AutomationExecutionId'],'Reject' )


        return result_output