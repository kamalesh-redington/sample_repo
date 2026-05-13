from hdbcli import dbapi

# SAP HANA Cloud connection details
HOST = "a5e6f9b0-7d2b-44b1-bfa2-9934b43a4ad6.hana.prod-in30.hanacloud.ondemand.com"
PORT = 443
USER = "SAKSOFT"
PASSWORD = "Welcome@1234567"

try:
    # Connect to SAP HANA Cloud
    connection = dbapi.connect(
        address=HOST,
        port=PORT,
        user=USER,
        password=PASSWORD,
        encrypt=True,
        sslValidateCertificate=False
    )

    print("Connected to SAP HANA Cloud!")

    cursor = connection.cursor()

    # Test Query
    cursor.execute("SELECT CURRENT_USER FROM DUMMY")

    result = cursor.fetchone()

    print("Current User:", result[0])

    cursor.close()
    connection.close()

except Exception as e:
    print("Connection Error:")
    print(e)