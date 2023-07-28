import http.server
import ssl
import os

host = '0.0.0.0'
port = 443

class MyHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = './index.html'
        return http.server.SimpleHTTPRequestHandler.do_GET(self)
    def send_response_only(self, code, message=None):
        super().send_response_only(code, message)
        self.send_header('Cache-Control', 'no-store, must-revalidate')
        self.send_header('Expires', '0')

def main():
    pwd = os.getcwd()
    try:
        # Use openssl to create a self signed certificate:
        # openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain('cert.pem', 'key.pem')
        print(f"Serving TLS")
        handler_object = MyHttpRequestHandler

        httpd = http.server.HTTPServer((host, port), handler_object)
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
        httpd.serve_forever()
    finally:
        os.chdir(pwd)

if __name__ == "__main__":
    main()




