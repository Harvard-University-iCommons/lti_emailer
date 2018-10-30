# Import smtplib for the actual sending function
import smtplib

# Import the email modules we'll need
from email.mime.text import MIMEText

from_addr = 'colin_murtaugh@harvard.edu'
to_addr = 'canvas-4998@mg.dev.tlt.harvard.edu'

# envelope_addr = from_addr
envelope_addr = 'prvs=764a7a4cd={}'.format(from_addr)

body = 'This is a message for testing the LTI emailer. Envelope address: {}'.format(envelope_addr)

msg = MIMEText(body)
msg['From'] = from_addr
msg['To'] = to_addr
msg['Subject'] = 'Test message'


s = smtplib.SMTP('mailhub.harvard.edu')
s.sendmail(envelope_addr, [to_addr], msg.as_string())
s.quit()
