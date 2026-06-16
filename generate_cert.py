"""
生成自签名SSL证书用于HTTPS访问
"""
from OpenSSL import crypto
import os

def generate_self_signed_cert():
    """生成自签名证书"""

    # 创建证书目录
    cert_dir = os.path.join(os.path.dirname(__file__), 'certs')
    os.makedirs(cert_dir, exist_ok=True)

    # 生成密钥
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 2048)

    # 生成证书
    cert = crypto.X509()
    cert.get_subject().C = "CN"
    cert.get_subject().ST = "State"
    cert.get_subject().L = "City"
    cert.get_subject().O = "Organization"
    cert.get_subject().OU = "Organizational Unit"
    cert.get_subject().CN = "localhost"

    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(365*24*60*60)  # 1年有效期
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, 'sha256')

    # 保存证书和密钥
    cert_file = os.path.join(cert_dir, 'cert.pem')
    key_file = os.path.join(cert_dir, 'key.pem')

    with open(cert_file, "wb") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

    with open(key_file, "wb") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))

    print(f"✅ 证书生成成功！")
    print(f"证书位置: {cert_file}")
    print(f"密钥位置: {key_file}")
    print(f"\n使用HTTPS启动: python app.py")
    print(f"访问地址: https://localhost:5000")
    print(f"\n⚠️ 首次访问时浏览器会提示不安全，点击'高级' -> '继续访问'即可")

if __name__ == '__main__':
    try:
        generate_self_signed_cert()
    except Exception as e:
        print(f"❌ 证书生成失败: {e}")
        print(f"\n请先安装 pyOpenSSL:")
        print(f"python -m pip install pyOpenSSL")
