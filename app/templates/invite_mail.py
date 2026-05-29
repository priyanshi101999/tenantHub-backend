def get_invite_email_template(invite_link: str, expiry_time: str = "24 hours") -> str:
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color:#f4f4f4; padding:20px;">
        <div style="max-width:600px; margin:auto; background:#ffffff; padding:20px; border-radius:8px;">
            
            <h2 style="color:#333;">You're invited 🎉</h2>
            
            <p>You’ve been invited to join our platform.</p>
            
            <p>Click the button below to set your password and activate your account:</p>
            
            <div style="text-align:center; margin:30px 0;">
                <a href="{invite_link}" 
                   style="background-color:#4CAF50; color:white; padding:12px 20px; 
                          text-decoration:none; border-radius:5px; font-weight:bold;">
                   Set Your Password
                </a>
            </div>
            
            <p>If the button doesn’t work, copy and paste this link:</p>
            <p style="word-break:break-all;">
                <a href="{invite_link}">{invite_link}</a>
            </p>
            
            <p style="color:#888;">This link will expire in {expiry_time}.</p>
            
            <p>If you did not expect this invitation, you can safely ignore this email.</p>
            
            <br>
            <p>Thanks,<br>Your Team</p>
        </div>
    </body>
    </html>
    """