# app/core/plan_features.py

PLAN_FEATURES = {
    "FREE": {
        "max_tasks"        : 20,
        "max_users"        : 5,
        "file_attachments" : False,
        "push_notifications": False,
        "email_notifications": False
    },
    "PRO": {
        "max_tasks"        : 500,
        "max_users"        : 25,
        "file_attachments" : True,
        "push_notifications": True,
        "email_notifications": True,
    },
    "ENTERPRISE": {
        "max_tasks"        : 999999,
        "max_users"        : 999999,
        "file_attachments" : True,
        "push_notifications": True,
        "email_notifications": True
    },
}
