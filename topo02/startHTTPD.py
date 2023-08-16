import http.server
import socketserver

class MyHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = './index.html'
        return http.server.SimpleHTTPRequestHandler.do_GET(self)
    def send_response_only(self, code, message=None):
        super().send_response_only(code, message)
        self.send_header('Cache-Control', 'no-store, must-revalidate')
        self.send_header('Expires', '0')

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True
    
# Create an object of the above class
handler_object = MyHttpRequestHandler

PORT = 80
my_server = ReusableTCPServer(("", PORT), handler_object)

# Star the server
my_server.serve_forever()
