# Proxy Buster

[![Code Climate](https://codeclimate.com/github/gszathmari/proxy-buster/badges/gpa.svg)](https://codeclimate.com/github/gszathmari/proxy-buster)

Analyze mirrors of any website for injected JavaScript code

This application retrieves the HTML page of a website and its mirrors, then analyses its code for additional scripts (ads, exploit kits etc.) that evil mirrors may inject

## Usage

### Prerequisites

Install packages as the following:

```sh
$ pip install -r requirements.txt
```

### Running

Run the script as the following:

```sh
$ python buster.py -u <original website URL> [<mirror website URL>, ...]
```

#### Switches

* ``-u, --url``: Original website to compare the mirrors
* ``-i, --inline``: (optional) Compare inline scripts
* ``-e, --external``: (optional) Compare URLs pointing to external scripts
* ``-v, --verbose``: (optional) Dump contents of inline and external scripts to command-line
* ``-o, --output``: (optional) Write result statistics into a CSV file
* ``-m, --mirror-list``: (optional) Supply list of mirrors from file instead the command-line. One URL per line.
* ``-f, --file``: (optional) Store raw HTTP responses in this file instead of ``mirrors.dat``
* ``-n, --nocheck``: (optional) Get HTTP responses from raw file instead of the Internet

#### Data File

HTTP responses are stored on disk in ``mirrors.dat`` instead of memory. This allows to store raw results or resume operations for later.

## Documentation

### Comparing Inline Scripts

This test will return the number of additional inline scripts on website mirrors

```sh
$ python buster.py -i -u <original website URL> [<mirror website URL>, ...]
```

The application parses the HTML code of the original and mirror websites and extracts inline scripts between `<script></script>` tags. In case a mirror is injecting additional JavaScript code, the application will return the total number. When `-v` switch is on, it will also list the contents of these additional scripts.

### Comparing External Script URLs

This test will return the number of additional URLs pointing to external scripts

```sh
$ python buster.py -e -u <original website URL> [<mirror website URL>, ...]
```

The application parses the HTML and extracts URLs from `<script src="">` tags. If a mirror is injecting additional `<script src="">` tags, the application will return the number of extra URLs. When `-v` switch is on, it will also list these additional links.

### Comparing External Assets

This test will compare external scripts for modified code

```sh
$ python buster.py -a -u <original website URL> [<mirror website URL>, ...]
```

The application parses the HTML and extracts URLs from `<script src="">` tags. In this case however, the test downloads these assets in case the path of the URL is matching. In case a mirror is injecting additional JavaScript into external scripts such as jQuery, it will return the differences.

### Creating Statistics

This will execute all of the tests listed above and print results into a CSV file. This comes handy if we compare a website with a long list of mirrors.

```sh
$ python buster.py -o <filename> -u <original website URL> [<mirror website URL>, ...]
```

## Contribute

Pull requests are welcome

### Contributors

- [Gabor Szathmari](http://gaborszathmari.me) - [@gszathmari](https://twitter.com/gszathmari)

## Credits

This project was inspired by the following project:

* [Analyzing 443 free proxies - Only 21% are not shady](https://blog.haschek.at/2015-analyzing-443-free-proxies)

The project was first featured on the [Rainbow and Unicorn](https://blog.gaborszathmari.me/2015/08/05/malware-injecting-torrent-mirrors/) security blog

## License

See the [LICENSE](LICENSE) file for license rights and limitations (MIT)
