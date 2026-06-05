"""Constants for the multi-user scale router integration."""

from __future__ import annotations

DOMAIN = "multi_user_scale_router"

CONF_SOURCE_ENTITY_ID = "source_entity_id"

CONF_TRACKED_METRICS = "tracked_metrics"
CONF_PERSON_ENTITY = "person_entity"
CONF_MOBILE_NOTIFY_SERVICES = "mobile_notify_services"
CONF_HISTORY_RETENTION_DAYS = "history_retention_days"
CONF_MAX_HISTORY_SIZE = "max_history_size"
CONF_MIN_TOLERANCE_KG = "min_tolerance_kg"
CONF_SETTLING_DELAY = "settling_delay"

SYSTEM_ATTRIBUTES = {
    "friendly_name",
    "unit_of_measurement",
    "device_class",
    "state_class",
    "icon",
    "restored",
    "supported_features",
    "attribution",
    "entity_picture",
    "assumed_state",
    "mac",
    "mac_address",
    "device_id",
    "rssi",
    "battery",
    "battery_level",
}

SERVICE_ASSIGN_MEASUREMENT = "assign_measurement"
SERVICE_REASSIGN_MEASUREMENT = "reassign_measurement"
SERVICE_REMOVE_MEASUREMENT = "remove_measurement"
SERVICE_MOVE_MEASUREMENT_COMPONENT = "move_measurement_component"
SERVICE_REMOVE_MEASUREMENT_COMPONENT = "remove_measurement_component"
CONF_DEVICE_ID = "device_id"
CONF_MEASUREMENT_ID = "measurement_id"
CONF_TARGET_MEASUREMENT_ID = "target_measurement_id"
CONF_USER_ID = "user_id"
CONF_FROM_USER_ID = "from_user_id"
CONF_TO_USER_ID = "to_user_id"
CONF_COMPONENT = "component"
CONF_METRIC_KEY = "metric_key"
CONF_ROUTER_STATE = "router_state"

COMPONENT_WEIGHT = "weight"
COMPONENT_TRACKED_METRIC = "tracked_metric"

DATA_ROUTER = "multi_user_scale_router_data"
DATA_MOBILE_APP_LISTENER_UNSUB = "multi_user_scale_router_mobile_app_listener_unsub"

ATTR_UNIT = "unit_of_measurement"

DEFAULT_HISTORY_RETENTION_DAYS = 90
DEFAULT_MAX_HISTORY_SIZE = 100
DEFAULT_MIN_TOLERANCE_KG = 1.5
DEFAULT_SETTLING_DELAY = 2.0
MAX_PENDING_MEASUREMENTS = 10
