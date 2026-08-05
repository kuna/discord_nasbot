import dukpy
import pytest

from utils.js import evaljs, runjs


def test_basic():
    assert runjs("return 2 + 2") == "4"


def test_expression_without_return():
    assert runjs("2 + 2") == "4"


def test_function_body_with_statements():
    assert runjs("var a = 2; var b = 3; return a * b") == "6"


def test_string_result_is_returned_raw():
    assert runjs("'hello ' + 'world'") == "hello world"


@pytest.mark.parametrize(
    ("script", "expected"),
    [
        ("2.5 + 1", "3.5"),
        ("true", "true"),
        ("false", "false"),
        ("null", "null"),
        ("undefined", "null"),
        ("[1, 2, 3]", "[1, 2, 3]"),
        ("({a: 1})", '{"a": 1}'),
    ],
)
def test_result_formatting(script, expected):
    assert runjs(script) == expected


def test_es6_arrow_functions_and_template_strings():
    assert runjs("[1, 2, 3].map(x => x * 2).join(',')") == "2,4,6"
    assert runjs("var n = 2; return `n is ${n}`") == "n is 2"


def test_evaljs_returns_native_values():
    assert evaljs("2 + 2") == 4
    assert evaljs("[1, 2]") == [1, 2]
    assert evaljs("({a: 1})") == {"a": 1}
    assert evaljs("null") is None


def test_variables_are_passed_to_the_script():
    assert runjs("return dukpy['x'] * 3", x=7) == "21"


def test_syntax_error_is_raised():
    with pytest.raises(dukpy.JSRuntimeError, match="SyntaxError"):
        runjs("this is not javascript")


def test_runtime_error_is_raised():
    with pytest.raises(dukpy.JSRuntimeError):
        runjs("nope.notAFunction()")

def test_some_long_script():
    long_script = """
domain2 = "goa.com"

gg = { m: function(g) {
var o = 0;
switch (g) {
case 2877:
case 1480:
    o = 1; break;
}
return o;
},
s: function(h) { var m = /(..)(.)$/.exec(h); return parseInt(m[2]+m[1], 16).toString(10); },
b: '1785801601/'
};

function subdomain_from_url(url, base, dir) {
        var retval = '';
        if (!base) {
                if (dir === 'webp') {
                        retval = 'w';
                } else if (dir === 'avif') {
                        retval = 'a';
                }
        }
        
        var b = 16;
        
        var r = /\/[0-9a-f]{61}([0-9a-f]{2})([0-9a-f])/;
        var m = r.exec(url);
        if (!m) {
                return retval;
        }
        
        var g = parseInt(m[2]+m[1], b);
        if (!isNaN(g)) {
                if (base) {
                        retval = String.fromCharCode(97 + gg.m(g)) + base;
                } else {
                        retval = retval + (1+gg.m(g));
                }
        }
        
        return retval;
}

function url_from_url(url, base, dir) {
        return url.replace(/\/\/..?\.(?:goa\.com)\//, '//'+subdomain_from_url(url, base, dir)+'.'+domain2+'/');
}


function full_path_from_hash(hash) {
        return gg.b+gg.s(hash)+'/'+hash;
}

function real_full_path_from_hash(hash) {
        return hash.replace(/^.*(..)(.)$/, '$2/$1/'+hash);
}


function url_from_hash(galleryid, image, dir, ext) {
        ext = ext || dir || image.name.split('.').pop();
        if (dir === 'webp' || dir === 'avif') {
                dir = '';
        } else {
                dir += '/';
        }

        return 'https://a.'+domain2+'/'+dir+full_path_from_hash(image.hash)+'.'+ext;
}

function url_from_url_from_hash(galleryid, image, dir, ext, base) {
        if ('tn' === base) {
                return url_from_url('https://a.'+domain2+'/'+dir+'/'+real_full_path_from_hash(image.hash)+'.'+ext, base);
        }
        return url_from_url(url_from_hash(galleryid, image, dir, ext), base, dir);
}
"""
    prepare_script = "file={\"name\": \"04.jpg\", \"hash\": \"a2c0342a2617026fbaeed01130c826cc3f58242799894b3ecc1abfa811ede03f\"}"
    main_script = "url_from_url_from_hash(\"4095257\", file, \"webp\")"
    val = runjs(f"{long_script}; {prepare_script}; return {main_script};")
    assert val == "https://w1.goa.com/1785801601/3843/a2c0342a2617026fbaeed01130c826cc3f58242799894b3ecc1abfa811ede03f.webp"
