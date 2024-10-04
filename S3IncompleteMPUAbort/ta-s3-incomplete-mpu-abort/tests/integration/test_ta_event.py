import logging
import os
from time import sleep, time
from unittest import TestCase

import boto3
from botocore.exceptions import ClientError

"""
Make sure env variable AWS_SAM_STACK_NAME exists with the name of the stack we are going to test. 
"""

class TestS3LifecyclePolicy(TestCase):
    """
    This integration test will create an S3 bucket without a lifecycle policy,
    trigger the Trusted Advisor check, and verify the lambda function is invoked
    by checking the cloudwatch log and the applied lifecycle policy.
    The S3 bucket will be deleted when the test completes.
    """

    function_name: str
    bucket_name: str  # temporary S3 bucket name

    @classmethod
    def get_and_verify_stack_name(cls) -> str:
        stack_name = os.environ.get("AWS_SAM_STACK_NAME")
        if not stack_name:
            raise Exception(
                "Cannot find env var AWS_SAM_STACK_NAME. \n"
                "Please setup this environment variable with the stack name where we are running integration tests."
            )

        # Verify stack exists
        client = boto3.client("cloudformation")
        try:
            client.describe_stacks(StackName=stack_name)
        except Exception as e:
            raise Exception(
                f"Cannot find stack {stack_name}. \n" f'Please make sure stack with the name "{stack_name}" exists.'
            ) from e

        return stack_name

    @classmethod
    def setUpClass(cls) -> None:
        stack_name = TestS3LifecyclePolicy.get_and_verify_stack_name()

        client = boto3.client("cloudformation")
        response = client.list_stack_resources(StackName=stack_name)
        resources = response["StackResourceSummaries"]
        function_resources = [
            resource for resource in resources if resource["LogicalResourceId"] == "ApplyLifecycleFunction"
        ]
        if not function_resources:
            raise Exception("Cannot find ApplyLifecycleFunction")

        cls.function_name = function_resources[0]["PhysicalResourceId"]

    def setUp(self) -> None:
        self.s3_client = boto3.client("s3")
        self.bucket_name = f"test-bucket-{int(time())}"
        self.s3_client.create_bucket(Bucket=self.bucket_name)

    def tearDown(self) -> None:
        # Delete all objects in the bucket
        response = self.s3_client.list_objects_v2(Bucket=self.bucket_name)
        if 'Contents' in response:
            for obj in response['Contents']:
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=obj['Key'])
        
        # Delete the bucket
        self.s3_client.delete_bucket(Bucket=self.bucket_name)

    def test_s3_lifecycle_policy(self):
        log_group_name = f"/aws/lambda/{self.function_name}"

        # Trigger Trusted Advisor check (this is a placeholder, as we can't directly trigger TA checks)
        # In a real scenario, you might need to wait for the next TA refresh or use the Support API if available
        self._simulate_ta_check()

        # Wait for the Lambda function to be invoked (adjust the wait time as needed)
        sleep(30)

        # Verify the lifecycle policy was applied
        try:
            response = self.s3_client.get_bucket_lifecycle_configuration(Bucket=self.bucket_name)
            rules = response.get('Rules', [])
            self.assertTrue(any(rule.get('ID') == 'AbortIncompleteMultipartUploads' for rule in rules),
                            "Expected lifecycle rule was not found")
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchLifecycleConfiguration':
                self.fail("No lifecycle configuration was applied")
            else:
                raise

        # Verify Lambda function logs
        self._verify_lambda_logs(log_group_name)

    def _simulate_ta_check(self):
        # This is a placeholder method to simulate triggering a Trusted Advisor check
        # In a real integration test, you might need to use the AWS Support API to refresh the check
        # or wait for the next scheduled refresh
        pass

    def _verify_lambda_logs(self, log_group_name: str):
        # Verify that the Lambda function was invoked and processed our test bucket
        retries = 5
        start_time = int(time() - 300) * 1000  # Look at logs from the last 5 minutes
        while retries >= 0:
            log_stream_name = self._get_latest_log_stream_name(log_group_name)
            if not log_stream_name:
                sleep(10)
                continue

            match_events = self._get_matched_events(log_group_name, log_stream_name, start_time)
            if match_events:
                return
            else:
                logging.info(f"Cannot find matching events containing bucket name {self.bucket_name}, waiting")
                retries -= 1
                sleep(10)

        self.fail(f"Cannot find matching events containing bucket name {self.bucket_name} after 5 retries")

    def _get_latest_log_stream_name(self, log_group_name: str):
        client = boto3.client("logs")
        try:
            response = client.describe_log_streams(
                logGroupName=log_group_name,
                orderBy="LastEventTime",
                descending=True,
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                logging.info(f"Cannot find log group {log_group_name}, waiting")
                return None
            raise e

        log_streams = response["logStreams"]
        self.assertTrue(log_streams, "Cannot find log streams")

        return log_streams[0]["logStreamName"]

    def _get_matched_events(self, log_group_name, log_stream_name, start_time):
        client = boto3.client("logs")
        response = client.get_log_events(
            logGroupName=log_group_name,
            logStreamName=log_stream_name,
            startTime=start_time,
            endTime=int(time()) * 1000,
            startFromHead=False,
        )
        events = response["events"]
        return [event for event in events if self.bucket_name in event["message"]]