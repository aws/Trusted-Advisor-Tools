import boto3


def lambda_handler(event, context) -> dict:
    bucket_name = event["detail"]["check-item-detail"]["Bucket Name"]

    # Connect to S3
    s3 = boto3.client("s3")

    # If bucket has tag "DisableVersioning", do not enable versioning
    try:
        tags = s3.get_bucket_tagging(Bucket=bucket_name)
        if "DisableVersioning" in [tag["Key"] for tag in tags["TagSet"]]:
            return {
                "statusCode": 200,
                "body": f"Bucket versioning is intentionally disabled for {bucket_name}. You can exclude this bucket from this check via the Trusted Advisor console",
            }
    except Exception:
        pass

    # Set bucket versioning to enabled
    try:
        s3.put_bucket_versioning(
            Bucket=bucket_name, VersioningConfiguration={"Status": "Enabled"}
        )
        return {
            "statusCode": 200,
            "body": f"Bucket versioning enabled for {bucket_name}",
        }
    except Exception as e:
        print(e)
        return {"statusCode": 500, "body": f"Error: {e}"}
