#!/usr/bin/env python3
"""
Israeli Home Front Command Red Alert Monitor
Monitors the active alerts feed and publishes MQTT events.
"""

import json
import time
import logging
import requests
from datetime import datetime
from typing import Dict, Set, Optional
import paho.mqtt.client as mqtt
from dataclasses import dataclass
import os
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('red_alert_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class AlertConfig:
    """Configuration for the alert monitor"""
    # API Configuration
    alerts_url: str = "https://www.oref.org.il/warningMessages/alert/Alerts.json"
    poll_interval: int = 5  # seconds
    request_timeout: int = 10  # seconds
    
    # Location Configuration
    target_area: str = "רחובות"  # Example default
    
    # MQTT Configuration
    mqtt_broker: str = "192.168.0.44"
    mqtt_port: int = 1883
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None
    mqtt_client_id: str = "red_alert_monitor"
    
    # MQTT Topics
    topic_prewarning: str = "redalert/prewarning"
    topic_active: str = "redalert/active"
    topic_allclear: str = "redalert/allclear"
    
    @classmethod
    def from_env(cls) -> 'AlertConfig':
        """Load configuration from environment variables"""
        return cls(
            alerts_url=os.getenv('ALERTS_URL', cls.alerts_url),
            poll_interval=int(os.getenv('POLL_INTERVAL', cls.poll_interval)),
            request_timeout=int(os.getenv('REQUEST_TIMEOUT', cls.request_timeout)),
            target_area=os.getenv('TARGET_AREA', cls.target_area),
            mqtt_broker=os.getenv('MQTT_BROKER', cls.mqtt_broker),
            mqtt_port=int(os.getenv('MQTT_PORT', cls.mqtt_port)),
            mqtt_username=os.getenv('MQTT_USERNAME'),
            mqtt_password=os.getenv('MQTT_PASSWORD'),
            mqtt_client_id=os.getenv('MQTT_CLIENT_ID', cls.mqtt_client_id),
            topic_prewarning=os.getenv('TOPIC_PREWARNING', cls.topic_prewarning),
            topic_active=os.getenv('TOPIC_ACTIVE', cls.topic_active),
            topic_allclear=os.getenv('TOPIC_ALLCLEAR', cls.topic_allclear),
        )

class AlertState:
    """Tracks the current alert state for the monitored area"""
    
    def __init__(self):
        self.current_state: Optional[str] = None  # None, 'prewarning', 'active', 'allclear'
        self.last_alert_time: Optional[datetime] = None
        self.active_alerts: Set[str] = set()
        
    def update_state(self, new_state: str, alert_time: datetime) -> bool:
        """
        Update the alert state and return True if state changed
        """
        if self.current_state != new_state:
            logger.info(f"Alert state changed: {self.current_state} -> {new_state}")
            self.current_state = new_state
            self.last_alert_time = alert_time
            return True
        return False

class RedAlertMonitor:
    """Main monitor class for Israeli Home Front Command alerts"""
    
    def __init__(self, config: AlertConfig):
        self.config = config
        self.state = AlertState()
        self.mqtt_client = None
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def setup_mqtt(self) -> bool:
        """Initialize MQTT client connection"""
        try:
            # Remove deprecated callback_api_version to avoid warning
            self.mqtt_client = mqtt.Client(
                client_id=self.config.mqtt_client_id,
                protocol=mqtt.MQTTv311,
                transport="tcp"
            )
            
            if self.config.mqtt_username and self.config.mqtt_password:
                self.mqtt_client.username_pw_set(
                    self.config.mqtt_username, 
                    self.config.mqtt_password
                )
            
            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
            
            logger.info(f"Connecting to MQTT broker at {self.config.mqtt_broker}:{self.config.mqtt_port}")
            self.mqtt_client.connect(self.config.mqtt_broker, self.config.mqtt_port, 60)
            self.mqtt_client.loop_start()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup MQTT connection: {e}")
            return False
    
    def _on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        """MQTT connection callback"""
        if rc == 0:
            logger.info("Successfully connected to MQTT broker")
        else:
            logger.error(f"Failed to connect to MQTT broker with code {rc}")
    
    def _on_mqtt_disconnect(self, client, userdata, rc, properties=None):
        """MQTT disconnection callback"""
        logger.warning(f"Disconnected from MQTT broker with code {rc}")
    
    def publish_mqtt_event(self, topic: str, payload: Dict) -> bool:
        """Publish an event to MQTT"""
        try:
            if not self.mqtt_client:
                logger.error("MQTT client not initialized")
                return False
                
            json_payload = json.dumps(payload, ensure_ascii=False)
            result = self.mqtt_client.publish(topic, json_payload, qos=1, retain=True)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Published to {topic}: {json_payload}")
                return True
            else:
                logger.error(f"Failed to publish to {topic}: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Error publishing MQTT event: {e}")
            return False
    
    def fetch_alerts(self) -> Optional[list]:
        """Fetch current alerts from the Home Front Command API"""
        try:
            logger.debug(f"Fetching alerts from {self.config.alerts_url}")
            response = self.session.get(
                self.config.alerts_url,
                timeout=self.config.request_timeout
            )
            response.raise_for_status()
            
            # Decode using 'utf-8-sig' to remove BOM if present
            text = response.content.decode('utf-8-sig').strip()
            
            if not text:
                logger.debug("No active alerts (empty response)")
                return []
            
            alerts = json.loads(text)
            logger.debug(f"Received {len(alerts)} alerts")
            return alerts
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch alerts: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse alerts JSON: {e}")
            return None
    
    def process_alerts(self, alerts: list) -> None:
        """Process alerts and update state accordingly"""
        if not alerts:
            # No active alerts - check if we need to send all clear
            if self.state.current_state in ['prewarning', 'active']:
                self.handle_all_clear()
            else:
                logger.info("There are no alerts in the target area, everything is good.")
            return
        
        target_area_alerts = [
            alert for alert in alerts 
            if alert.get('data') == self.config.target_area
        ]
        
        if not target_area_alerts:
            # No alerts for our target area
            if self.state.current_state in ['prewarning', 'active']:
                self.handle_all_clear()
            else:
                logger.info("There are no alerts in the target area, everything is good.")
            return
        
        # Process alerts for the target area
        for alert in target_area_alerts:
            self.process_single_alert(alert)
    
    def process_single_alert(self, alert: Dict) -> None:
        """Process a single alert for the target area"""
        try:
            category = alert.get('category')
            title = alert.get('title', '')
            alert_date = alert.get('alertDate', '')
            data = alert.get('data', '')
            
            # Parse alert timestamp safely
            try:
                alert_time = datetime.strptime(alert_date, '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                alert_time = datetime.now()
            
            logger.info(f"Processing alert: Category {category}, Title: {title}, Area: {data}")
            
            # Determine alert type based on category
            if category == 14:  # Prewarning
                self.handle_prewarning(alert, alert_time)
            elif category == 1:   # Active red alert
                self.handle_active_alert(alert, alert_time)
            elif category == 13:  # All clear
                self.handle_all_clear_alert(alert, alert_time)
            else:
                logger.warning(f"Unknown alert category: {category}")
                
        except Exception as e:
            logger.error(f"Error processing alert: {e}")
    
    def handle_prewarning(self, alert: Dict, alert_time: datetime) -> None:
        """Handle prewarning alert"""
        if self.state.update_state('prewarning', alert_time):
            payload = {
                'timestamp': alert_time.isoformat(),
                'area': self.config.target_area,
                'alert_type': 'prewarning',
                'title': alert.get('title', ''),
                'message': 'Pre-warning alert - Take shelter immediately'
            }
            self.publish_mqtt_event(self.config.topic_prewarning, payload)
    
    def handle_active_alert(self, alert: Dict, alert_time: datetime) -> None:
        """Handle active red alert"""
        if self.state.update_state('active', alert_time):
            payload = {
                'timestamp': alert_time.isoformat(),
                'area': self.config.target_area,
                'alert_type': 'active',
                'title': alert.get('title', ''),
                'message': 'ACTIVE RED ALERT - TAKE SHELTER NOW'
            }
            self.publish_mqtt_event(self.config.topic_active, payload)
    
    def handle_all_clear_alert(self, alert: Dict, alert_time: datetime) -> None:
        """Handle all clear alert from API"""
        if self.state.update_state('allclear', alert_time):
            payload = {
                'timestamp': alert_time.isoformat(),
                'area': self.config.target_area,
                'alert_type': 'allclear',
                'title': alert.get('title', ''),
                'message': 'All clear - Threat has ended'
            }
            self.publish_mqtt_event(self.config.topic_allclear, payload)
    
    def handle_all_clear(self) -> None:
        """Handle implicit all clear (no alerts in feed)"""
        if self.state.update_state('allclear', datetime.now()):
            payload = {
                'timestamp': datetime.now().isoformat(),
                'area': self.config.target_area,
                'alert_type': 'allclear',
                'title': 'No active alerts',
                'message': 'All clear - No active threats'
            }
            self.publish_mqtt_event(self.config.topic_allclear, payload)
    
    def run(self) -> None:
        """Main monitoring loop"""
        logger.info("Starting Red Alert Monitor")
        logger.info(f"Target area: {self.config.target_area}")
        logger.info(f"Poll interval: {self.config.poll_interval} seconds")
        
        if not self.setup_mqtt():
            logger.error("Failed to setup MQTT connection. Exiting.")
            return
        
        try:
            while True:
                alerts = self.fetch_alerts()
                if alerts is not None:
                    self.process_alerts(alerts)
                else:
                    logger.warning("Failed to fetch alerts, will retry next cycle")
                
                time.sleep(self.config.poll_interval)
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
        finally:
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            logger.info("Red Alert Monitor stopped")

def main():
    """Main entry point"""
    # Load configuration from environment or use defaults
    config = AlertConfig.from_env()
    
    # Create and run monitor
    monitor = RedAlertMonitor(config)
    monitor.run()

if __name__ == "__main__":
    main()
