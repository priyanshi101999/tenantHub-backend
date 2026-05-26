def otp_email_template(otp):
    return  f"""
    <h2>Email Verification</h2>
    <p>Your OTP is:</p>
    <h1>{otp}</h1>
    <p>This OTP is valid for 5 minutes.</p>
    """