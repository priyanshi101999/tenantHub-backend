# app/core/plan_features.py

PLAN_FEATURES = {
    "FREE": {
        "max_tasks"        : 20,
        "max_users"        : 5,
        "file_attachments" : False,
        "analytics"        : False,
        "webhooks"         : False,
        "push_notifications": False,
        "sms_notifications" : False
    },
    "PRO": {
        "max_tasks"        : 500,
        "max_users"        : 25,
        "file_attachments" : True,
        "analytics"        : True,
        "webhooks"         : False,
        "push_notifications": True,
        "sms_notifications" : True,
    },
    "ENTERPRISE": {
        "max_tasks"        : 999999,
        "max_users"        : 999999,
        "file_attachments" : True,
        "analytics"        : True,
        "webhooks"         : True,
        "push_notifications": True,
        "sms_notifications" : True
    },
}