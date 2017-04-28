import imaplib
from contextlib import contextmanager
import re
import email
import email.header


class MailClient(object):

    class JSONSerializable(object):

        def JSONrepr(self):
            return self.__dict__

    class Folder(JSONSerializable):

        def __init__(self, name, path, status):
            self.name = name
            self.path = path
            self.status = status
            self.mails = []

    class Mail(JSONSerializable):

        def __init__(self, headers, body):
            self.headers = headers
            self.body = body

        def decode_mime_words(s):
            return u''.join(
                word.decode(encoding or 'utf8') if isinstance(word, bytes) else word
                for word, encoding in email.header.decode_header(s))

        def __str__(self):
            sbuf = ''
            for k, v in self.headers.items():
                sbuf += '{0}: {1}\n'.format(k, v)
            sbuf += '\nBody:\n\n{0}'.format(self.decode_mime_words(self.body))
            return sbuf

    class IMAPSession(object):

        FOLDER_REGEX = r"(?P<status>\([\\\w\s]+\))\s\"(?P<path>[\w\s\/\\]+)\"\s*\"{0,1}(?P<name>.*)\"{0,1}"
        HEADER_REGEX = r"(?P<name>\w+)\s*\:\s*(?P<value>.+)"
        MAIL_REGEX = r"{0}*(?P<body>.*)".format(HEADER_REGEX)

        HEADERS = ['from', 'to', 'subject']

        def __init__(self, imap_client, mailboxes):
            self.client = imap_client
            self.mailboxes = mailboxes
            self.folders = []
            self.folder_re = re.compile(self.FOLDER_REGEX)
            self.header_re = re.compile(self.HEADER_REGEX, re.MULTILINE)
            self.mail_re = re.compile(self.MAIL_REGEX, re.MULTILINE)
            self.get_folders()

        def handle_op_reponse(self, response):
            if response != 'OK':
                raise

        def get_folders(self):
            op_status, folders = self.client.list()
            self.handle_op_reponse(op_status)
            for folder in folders:
                self.__parse_folder(folder)

        def __parse_folder(self, folder):
            match = self.folder_re.match(folder)
            if match is not None:
                folder_dict = match.groupdict()
                status = re.findall('\w+', folder_dict['status'])
                if folder_dict['name'] in self.mailboxes:
                    folder = MailClient.Folder(folder_dict['name'],
                                               folder_dict['path'],
                                               status)
                    self.folders.append(folder)

        def get_mails(self):
            for folder in self.folders:
                folder.mails = []
                op_status, [mail_count] = self.client.select(folder.name)
                self.handle_op_reponse(op_status)
                if(int(mail_count) > 0):
                    op_status, [mail_ids] = self.client.search(None, 'UNSEEN')
                    mail_ids = mail_ids.split(' ')
                    if(mail_ids[0] == ''):
                        continue
                    for mail_id in mail_ids:
                        try:
                            mail_id = int(mail_id)
                        except ValueError:
                            continue
                        op_status, data = self.client.fetch(
                            mail_id, '(BODY.PEEK[])')
                        self.handle_op_reponse(op_status)
                        parsed_mail = email.message_from_string(data[0][1])
                        if parsed_mail.is_multipart():
                            for part in parsed_mail.walk():
                                if type(part.get_payload()) == str:
                                    parsed_mail['body'] = part.get_payload()
                        else:
                            parsed_mail['body'] = parsed_mail.get_payload()

                        mail = MailClient.Mail(
                            {h: parsed_mail[h] for h in self.HEADERS
                             if parsed_mail[h] is not None},
                            parsed_mail['body'])
                        folder.mails.append(mail)
                self.client.close()

    def __init__(self, cfg):
        self.host = cfg.get('server')
        self.port = cfg.get('port')
        self.uname = cfg.get('username')
        self.passw = cfg.get('password')
        self.mailboxes = cfg.get('mailboxes')
        self.imap_client = None

    @contextmanager
    def creatse_session_scope(self):
        print("Connecting to {0}:{1}".format(self.host, self.port))
        try:
            self.imap_client = imaplib.IMAP4(self.host, self.port)
            self.imap_client.login(self.uname, self.passw)
            session = self.IMAPSession(self.imap_client, self.mailboxes)
            yield session
        except Exception:
            raise
        finally:
            self.imap_client.logout()

    def create_session(self):
        self.imap_client = imaplib.IMAP4(self.host, self.port)
        self.imap_client.login(self.uname, self.passw)
        return self.IMAPSession(self.imap_client, self.mailboxes)

