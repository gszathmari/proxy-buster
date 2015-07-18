# Proxy Buster

Analyze mirrors of any website for injected JavaScript code

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

Use one or more of the following switches:

* ``-i, --inline``: Compare inline scripts
* ``-e, --external``: Compare URLs pointing to external scripts
* ``-a, --assets``: Compare matching external scripts
* ``-o, --output``: Write test statistics into file

## Documentation

### Comparing Inline Scripts

This test will return the number of additional inline scripts on website mirrors

The application parses the HTML code of the original and mirror websites and extracts inline scripts between `<script>` tags. In case a mirror is injecting additional JavaScript code, the application will return the total number. When `-v` switch is on, it will also list the contents of these additional scripts.

### Comparing External Script URLs

This test will return the number of additional URLs pointing to external scripts

The application parses the HTML and extracts URLs from `<script src="">` tags. If a mirror is injecting additional `<script src="">` tags, the application will return the number of extra URLs. When `-v` switch is on, it will also list these additional links.

### Comparing External Assets

This test will compare external scripts for modified code

The application parses the HTML and extracts URLs from `<script src="">` tags. In this case however, the test downloads these assets in case the path of the URL is matching. In case a mirror is injecting additional JavaScript into external scripts such as jQuery, it will return the differences.

### Creating Statistics

This will execute all of the tests listed above and print results into a CSV file. This comes handy if we compare a website with a long list of mirrors.

## Contribute

Pull requests are welcome

### Contributors

- [Gabor Szathmari](http://gaborszathmari.me) - [@gszathmari](https://twitter.com/gszathmari)

## Credits

This project was inspired by the following project:

* [Analyzing 443 free proxies - Only 21% are not shady](https://blog.haschek.at/2015-analyzing-443-free-proxies)

The project was first featured on the [Rainbow and Unicorn](https://blog.gaborszathmari.me/) security blog

## License

See the [LICENSE](LICENSE) file for license rights and limitations (MIT)
