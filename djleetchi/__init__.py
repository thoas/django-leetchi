from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from leetchi.api import LeetchiAPI


ERROR_CODES = {
    '01913': [_('Your bank account will not be charged. We invite you to renew your support now.'), ],
    '01119': [_('Your bank account will not be charged. We invite you to renew your support now.'), ],
    '01909': [_('Your bank account will not be charged. We invite you to renew your support now.'), ],
    '01904': [_('Your bank account will not be charged. We invite you to renew your support now.'), ],
    '01902': [_('Your bank account will not be charged. We invite you to renew your support now.'), ],
    '02317': [_('Your bank account will not be charged. We invite you to renew your support now.'), ],
    '01100': [
        _('It appears that your bank can not accept the payment, your account will not be charged. Thank you for trying again in a few hours / days or to contact your bank.'),
        _('There are several possible explanations to this problem: you have exceeded your payment ceiling, your account does not have sufficient funds ...'),
    ],
    '01200': [
        _('It appears that your bank can not accept the payment, your account will not be charged. Thank you for trying again in a few hours / days or to contact your bank.'),
        _('There are several possible explanations to this problem: you have exceeded your payment ceiling, your account does not have sufficient funds ...'),
    ],
    '01116': [
        _('It appears that your bank can not accept the payment, your account will not be charged. Thank you for trying again in a few hours / days or to contact your bank.'),
        _('There are several possible explanations to this problem: you have exceeded your payment ceiling, your account does not have sufficient funds ...'),
    ],
    '01121': [
        _('It appears that your bank can not accept the payment, your account will not be charged. Thank you for trying again in a few hours / days or to contact your bank.'),
        _('There are several possible explanations to this problem: you have exceeded your payment ceiling, your account does not have sufficient funds ...'),
    ],
    '01108': [
        _('It appears that your bank can not accept the payment, your account will not be charged. Thank you for trying again in a few hours / days or to contact your bank.'),
        _('There are several possible explanations to this problem: you have exceeded your payment ceiling, your account does not have sufficient funds ...'),
    ],
    '01120': [
        _('It appears that your bank can not accept the payment, your account will not be charged. Thank you for trying again in a few hours / days or to contact your bank.'),
        _('There are several possible explanations to this problem: you have exceeded your payment ceiling, your account does not have sufficient funds ...'),
    ],
    '01202': [
        _('Unfortunately, we are unable to accept your payment, your bank account will not be charged.'),
        _('If you contributed to projects on Ulule for more than 2500 euros during the calendar year, please contact the team Ulule (support@ulule.com) in order to uncap your user account.'),
    ],
    '04001': [
        _('Unfortunately, we are unable to accept your payment, your bank account will not be charged.'),
        _('If you contributed to projects on Ulule for more than 2500 euros during the calendar year, please contact the team Ulule (support@ulule.com) in order to uncap your user account.'),
    ],
    '04002': [
        _('Unfortunately, we are unable to accept your payment, your bank account will not be charged.'),
        _('If you contributed to projects on Ulule for more than 2500 euros during the calendar year, please contact the team Ulule (support@ulule.com) in order to uncap your user account.'),
    ],
    '01208': [_('Unfortunately, we are unable to accept your payment, your bank account will not be charged.'), ],
    '01125': [_('Unfortunately, we are unable to accept your payment, your bank account will not be charged.'), ],
    '01122': [_('Unfortunately, we are unable to accept your payment, your bank account will not be charged.'), ],
    '01206': [_('Unfortunately, we are unable to accept your payment, your bank account will not be charged.'), ],
    '03022': [
        _('It looks like you have faced difficulties when checking your credit card, your account will not be charged. This step is mandatory (3D-Secure standard) to ensure secured payments.'),
        _('Different ways exist to validate your payment with a 3D-Secure check: code received by SMS, birthday date, etc. We invite you to contact your bank to know the process with your card.'),
    ],
    '01111': [_('It seems that credit card details provided are not correct. Please try again.'), ],
    '01118': [_('It seems that credit card details provided are not correct. Please try again.'), ],
    '01101': [_('It seems that credit card details provided are not correct. Please try again.'), ],
    '01201': [_('It seems that credit card details provided are not correct. Please try again.'), ],
}


API_PARTNER_ID = getattr(settings, 'LEETCHI_API_PARTNER_ID', 'partnerID')
API_PRIVATE_KEY = getattr(settings, 'LEETCHI_API_PRIVATE_KEY', 'file://path/to/private_key')
API_PRIVATE_KEY_PASSWORD = getattr(settings, 'LEETCHI_API_PRIVATE_KEY_PASSWORD', '$ecret')
API_USE_SANDBOX = getattr(settings, 'LEETCHI_API_USE_SANDBOX', True)
API_HOST = getattr(settings, 'LEETCHI_API_HOST', None)

handler = LeetchiAPI(API_PARTNER_ID, API_PRIVATE_KEY, API_PRIVATE_KEY_PASSWORD, sandbox=API_USE_SANDBOX, host=API_HOST)
