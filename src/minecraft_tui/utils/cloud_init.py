"""Cloud-init configuration utilities."""


def generate_cloud_init_config() -> str:
    """Generate cloud-init user data for server security and setup.

    Returns:
        Cloud-init YAML configuration string
    """
    return r"""#cloud-config

# Minecraft Server Security Configuration
# Automatically configures fail2ban and basic security hardening

package_update: true
package_upgrade: true

packages:
  - fail2ban
  - ufw

# Configure fail2ban
write_files:
  - path: /etc/fail2ban/jail.local
    content: |
      [DEFAULT]
      # Ban hosts for 1 hour
      bantime = 3600
      # Find time window of 10 minutes
      findtime = 600
      # Max 5 retries before ban
      maxretry = 5
      # Destination email for notifications (optional)
      destemail = root@localhost
      # Sender email
      sender = fail2ban@localhost
      # Action to take (ban and optionally send email)
      action = %(action_)s

      [sshd]
      enabled = true
      port = ssh
      logpath = %(sshd_log)s
      backend = %(sshd_backend)s
      maxretry = 3
      bantime = 1800

  - path: /etc/fail2ban/filter.d/minecraft-ddos.conf
    content: |
      # Fail2Ban filter for Minecraft connection spam/DDoS
      [Definition]
      failregex = ^.*\[Server thread/WARN\]: <HOST> lost connection: Disconnected$
                  ^.*\[User Authenticator #\d+/INFO\]: <HOST> lost connection: Disconnected$
      ignoreregex =

runcmd:
  # Enable and start fail2ban
  - systemctl enable fail2ban
  - systemctl start fail2ban

  # Configure UFW firewall
  - ufw --force enable
  - ufw default deny incoming
  - ufw default allow outgoing
  - ufw allow ssh
  - ufw allow 25565/tcp comment 'Minecraft'
  - ufw allow 25575/tcp comment 'Minecraft RCON'

  # Disable root password login (SSH key only)
  - sed -i 's/#PermitRootLogin yes/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
  - sed -i 's/PermitRootLogin yes/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
  - systemctl restart ssh

  # Set timezone to UTC
  - timedatectl set-timezone UTC

final_message: "Minecraft server security configuration completed after $UPTIME seconds"
"""
