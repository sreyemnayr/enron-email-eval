from domain.models import Email
from pathlib import Path
from datetime import datetime
from email.utils import parsedate_to_datetime
from email.parser import Parser, BytesParser
from typing import Literal
from rich.progress import track


def parse_email_file(file_path: Path, method: Literal["r", "rb"] = "r") -> Email:
    try:
        with open(file_path, method) as file:
            parser = Parser() if method == "r" else BytesParser()
            email_message = parser.parse(file)
            email = Email(
                filename=str(file_path).replace("/email-data/maildir/", ""),
                message_id=str(email_message.get("Message-ID", "")),
                date=parsedate_to_datetime(email_message.get("Date", "")),
                from_address=str(email_message.get("From", "")),
                to_addresses=str(email_message.get("To", "")).replace(",", " ").split(),
                cc_addresses=str(email_message.get("Cc", "")).replace(",", " ").split(),
                bcc_addresses=str(email_message.get("Bcc", ""))
                .replace(",", " ")
                .split(),
                subject=str(email_message.get("Subject", "")),
                body=str(email_message.get_payload()),
                headers={str(k): str(v) for k, v in email_message.items()},
            )
            return email
    except Exception as e:
        if method == "r":
            return parse_email_file(file_path, "rb")
        else:
            raise e
