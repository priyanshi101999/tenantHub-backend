import enum

class Role(str, enum.Enum):
    ADMIN="ADMIN"
    USER="USER"

class Priority(str, enum.Enum):
    LOW="LOW"
    MEDIUM="MEDIUM"
    HIGH="HIGH"

class TaskStatus(str, enum.Enum):
    TODO="TODO"
    IN_PROGRESS="IN_PROGRESS"
    DONE="DONE"

class SubscriptionStatus(str, enum.Enum):
    ACTIVE="ACTIVE"
    INACTIVE="INACTIVE"
    CANCELED="CANCELED"
    PAST_DUE="PAST_DUE"