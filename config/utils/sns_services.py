import boto3
from botocore.exceptions import ClientError

from decouple import config


class SNSSMSService:
    def __init__(self, region='us-east-1'):
        self.sns = boto3.client(
            "sns",
            region_name=region,
            aws_access_key_id=config("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=config("AWS_SECRET_ACCESS_KEY"),
        )
    
    def send_sms(self, phone_number, message, sms_type='Transactional'):
        try:
            response = self.sns.publish(
                PhoneNumber=phone_number,
                Message=message,
                MessageAttributes={
                    'AWS.SNS.SMS.SMSType': {
                        'DataType': 'String',
                        'StringValue': sms_type
                    }
                }
            )
            return {
                'success': True,
                'message_id': response['MessageId']
            }
        except ClientError as e:
            return {
                'success': False,
                'error': str(e)
            }


sms_service = SNSSMSService(region=config("AWS_REGION_NAME"))
