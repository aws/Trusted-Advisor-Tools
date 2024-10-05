import pytest
from apply_lifecycle import app
from model.aws.ta import AWSEvent
from model.aws.ta import TAStateChangeNotification
from model.aws.ta import Marshaller

@pytest.fixture()
def eventBridgeTANotificationEvent():
    """ Generates EventBridge Trusted Advisor Notification Event"""
    return {
        "version": "0",
        "id": "89877641-0939-4fd1-9c4c-2f2d5d0c9d5c",
        "detail-type": "Trusted Advisor Check Item Refresh Notification",
        "source": "aws.trustedadvisor",
        "account": "123456789012",
        "time": "2023-04-15T18:43:48Z",
        "region": "us-east-1",
        "resources": [],
        "detail": {
            "check-name": "Amazon S3 Bucket Lifecycle Configuration",
            "check-item-detail": {
                "Status": "Yellow",
                "Region": "us-east-1",
                "Bucket Name": "example-bucket",
                "Lifecycle Rule for Deleting Incomplete MPU": "No",
                "Days After Initiation": ""
            },
            "status": "WARN",
            "resource_id": "arn:aws:s3:::example-bucket",
            "uuid": "c1cj39rr6v-1234-5678-9abc-def012345678"
        }
    }

def test_lambda_handler(eventBridgeTANotificationEvent, mocker):
    # Mock the apply_lifecycle_policy function
    mocker.patch('apply_lifecycle.app.apply_lifecycle_policy')

    # Call the lambda handler
    ret = app.lambda_handler(eventBridgeTANotificationEvent, "")

    # Unmarshall the returned event
    awsEventRet: AWSEvent = Marshaller.unmarshall(ret, AWSEvent)
    detailRet: TAStateChangeNotification = awsEventRet.detail

    # Assert that the function processed the event correctly
    assert detailRet.check_name == "Amazon S3 Bucket Lifecycle Configuration"
    assert detailRet.status == "WARN"
    assert detailRet.resource_id == "arn:aws:s3:::example-bucket"
    assert awsEventRet.detail_type.startswith("TALifecyclePolicyFunction processed event of ")

    # Assert that apply_lifecycle_policy was called with correct arguments
    app.apply_lifecycle_policy.assert_called_once_with("123456789012", "example-bucket")

def test_lambda_handler_ignore_compliant(eventBridgeTANotificationEvent, mocker):
    # Modify the event to simulate a compliant bucket
    eventBridgeTANotificationEvent['detail']['status'] = 'OK'

    # Mock the apply_lifecycle_policy function
    mock_apply = mocker.patch('apply_lifecycle.app.apply_lifecycle_policy')

    # Call the lambda handler
    ret = app.lambda_handler(eventBridgeTANotificationEvent, "")

    # Assert that apply_lifecycle_policy was not called
    mock_apply.assert_not_called()

    # Unmarshall the returned event
    awsEventRet: AWSEvent = Marshaller.unmarshall(ret, AWSEvent)
    
    # Assert that the function processed the event correctly
    assert awsEventRet.detail_type.startswith("TALifecyclePolicyFunction processed event of ")