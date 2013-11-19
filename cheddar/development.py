"""
Run a development server.
"""
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

from cheddar.app import create_app


def main():
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('-a',
                        dest='all_interfaces',
                        action='store_true',
                        default=False,
                        help='Listen on all interfaces')
    parser.add_argument('-p',
                        dest='port',
                        type=int,
                        default=5000,
                        help='Listen port')
    args, extra = parser.parse_known_args()

    app = create_app(debug=True)

    if args.all_interfaces:
        app.run(host='0.0.0.0',
                port=args.port)
    else:
        app.run(port=args.port)
