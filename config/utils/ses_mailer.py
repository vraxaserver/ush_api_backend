"""
ses_mailer.py

Lightweight AWS SES email sender.

Features:
- SendEmail for simple (text/html) emails (no attachments)
- SendRawEmail for emails with attachments
- Supports CC/BCC/Reply-To
- Minimal, reusable API

Requirements:
    pip install boto3

AWS auth:
- IAM role / env vars / ~/.aws/credentials supported by boto3
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple, Union

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from decouple import config


EmailStr = str
PathOrBytes = Union[str, bytes]


@dataclass(frozen=True)
class Attachment:
    """
    Attachment for SES raw emails.

    - filename: name shown in email client
    - content: raw bytes of the file
    - mime_type: e.g. 'application/pdf' (optional)
    """
    filename: str
    content: bytes
    mime_type: Optional[str] = None


class SESEmailError(RuntimeError):
    """Raised when SES send fails."""


class SESMailer:
    """
    SES mailer.

    region_name: SES region (e.g. 'us-east-1', 'eu-west-1')
    configuration_set: optional SES configuration set name
    source_arn / from_arn: optional identity ARN (if required by your SES setup)
    """

    def __init__(
        self,
        *,
        region_name: str,
        configuration_set: Optional[str] = None,
        source_arn: Optional[str] = None,
        from_arn: Optional[str] = None,
        client=None,
    ):
        self.client = client or boto3.client("ses", region_name=region_name)
        self.configuration_set = configuration_set
        self.source_arn = source_arn
        self.from_arn = from_arn

    @staticmethod
    def _as_list(x: Optional[Union[EmailStr, Sequence[EmailStr]]]) -> List[EmailStr]:
        if x is None:
            return []
        if isinstance(x, str):
            return [x]
        return list(x)

    def send(
        self,
        *,
        sender: EmailStr,
        to: Union[EmailStr, Sequence[EmailStr]],
        subject: str,
        text_body: Optional[str] = None,
        html_body: Optional[str] = None,
        cc: Optional[Union[EmailStr, Sequence[EmailStr]]] = None,
        bcc: Optional[Union[EmailStr, Sequence[EmailStr]]] = None,
        reply_to: Optional[Union[EmailStr, Sequence[EmailStr]]] = None,
        attachments: Optional[Sequence[Attachment]] = None,
        return_path: Optional[EmailStr] = None,
        tags: Optional[Sequence[Tuple[str, str]]] = None,
    ) -> str:
        """
        Send an email.

        Returns:
            SES MessageId string.
        """
        to_list = self._as_list(to)
        cc_list = self._as_list(cc)
        bcc_list = self._as_list(bcc)
        reply_to_list = self._as_list(reply_to)
        attachments = list(attachments or [])

        if not to_list and not cc_list and not bcc_list:
            raise ValueError("At least one recipient is required in to/cc/bcc.")

        if not (text_body or html_body):
            raise ValueError("Provide at least one of text_body or html_body.")

        try:
            if attachments:
                return self._send_raw(
                    sender=sender,
                    to_list=to_list,
                    cc_list=cc_list,
                    bcc_list=bcc_list,
                    subject=subject,
                    text_body=text_body,
                    html_body=html_body,
                    reply_to_list=reply_to_list,
                    attachments=attachments,
                    return_path=return_path,
                )
            else:
                return self._send_simple(
                    sender=sender,
                    to_list=to_list,
                    cc_list=cc_list,
                    bcc_list=bcc_list,
                    subject=subject,
                    text_body=text_body,
                    html_body=html_body,
                    reply_to_list=reply_to_list,
                    return_path=return_path,
                    tags=tags,
                )
        except (ClientError, BotoCoreError) as e:
            raise SESEmailError(str(e)) from e

    def _send_simple(
        self,
        *,
        sender: EmailStr,
        to_list: List[EmailStr],
        cc_list: List[EmailStr],
        bcc_list: List[EmailStr],
        subject: str,
        text_body: Optional[str],
        html_body: Optional[str],
        reply_to_list: List[EmailStr],
        return_path: Optional[EmailStr],
        tags: Optional[Sequence[Tuple[str, str]]],
    ) -> str:
        destination = {"ToAddresses": to_list}
        if cc_list:
            destination["CcAddresses"] = cc_list
        if bcc_list:
            destination["BccAddresses"] = bcc_list

        body = {}
        if text_body is not None:
            body["Text"] = {"Data": text_body, "Charset": "UTF-8"}
        if html_body is not None:
            body["Html"] = {"Data": html_body, "Charset": "UTF-8"}

        params = {
            "Source": sender,
            "Destination": destination,
            "Message": {
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": body,
            },
        }

        if reply_to_list:
            params["ReplyToAddresses"] = reply_to_list
        if return_path:
            params["ReturnPath"] = return_path
        if self.configuration_set:
            params["ConfigurationSetName"] = self.configuration_set
        if self.source_arn:
            params["SourceArn"] = self.source_arn
        if self.from_arn:
            params["FromArn"] = self.from_arn
        if tags:
            params["Tags"] = [{"Name": k, "Value": v} for k, v in tags]

        resp = self.client.send_email(**params)
        return resp["MessageId"]

    def _send_raw(
        self,
        *,
        sender: EmailStr,
        to_list: List[EmailStr],
        cc_list: List[EmailStr],
        bcc_list: List[EmailStr],
        subject: str,
        text_body: Optional[str],
        html_body: Optional[str],
        reply_to_list: List[EmailStr],
        attachments: List[Attachment],
        return_path: Optional[EmailStr],
    ) -> str:
        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = ", ".join(to_list) if to_list else ""
        if cc_list:
            msg["Cc"] = ", ".join(cc_list)
        if reply_to_list:
            msg["Reply-To"] = ", ".join(reply_to_list)

        # Alternative part (text + html)
        alt = MIMEMultipart("alternative")
        if text_body is not None:
            alt.attach(MIMEText(text_body, "plain", "utf-8"))
        if html_body is not None:
            alt.attach(MIMEText(html_body, "html", "utf-8"))

        msg.attach(alt)

        # Attach files
        for att in attachments:
            part = MIMEApplication(att.content)
            part.add_header("Content-Disposition", "attachment", filename=att.filename)
            msg.attach(part)

        raw_bytes = msg.as_string().encode("utf-8")

        # Destinations must include all recipients (To+Cc+Bcc) when using SendRawEmail
        destinations = list(dict.fromkeys(to_list + cc_list + bcc_list))  # stable unique

        params = {
            "Source": sender,
            "Destinations": destinations,
            "RawMessage": {"Data": raw_bytes},
        }

        if return_path:
            params["ReturnPath"] = return_path
        if self.configuration_set:
            params["ConfigurationSetName"] = self.configuration_set
        if self.source_arn:
            params["SourceArn"] = self.source_arn
        if self.from_arn:
            params["FromArn"] = self.from_arn

        resp = self.client.send_raw_email(**params)
        return resp["MessageId"]


def load_attachment(path: str, filename: Optional[str] = None, mime_type: Optional[str] = None) -> Attachment:
    """
    Helper to create an Attachment from a file path.
    """
    import os

    with open(path, "rb") as f:
        content = f.read()
    return Attachment(filename=filename or os.path.basename(path), content=content, mime_type=mime_type)


ses_client = boto3.client(
            "ses",
            region_name=config("AWS_REGION_NAME"),
            aws_access_key_id=config("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=config("AWS_SECRET_ACCESS_KEY"),
        )

ses_mailer = SESMailer(client=ses_client, region_name=config("AWS_REGION_NAME"))