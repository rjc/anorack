# Copyright © 2016-2018 Jakub Wilk <jwilk@jwilk.net>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the “Software”), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import contextlib
import io
import os
import sys
import tempfile

try:
    from unittest import mock
except ImportError:
    import mock  # pylint: disable=import-error

from nose.tools import (
    assert_equal,
    assert_not_equal,
)

from tests.tools import isolation

@contextlib.contextmanager
def tmpcwd():
    with tempfile.TemporaryDirectory(prefix='anorack.tests.') as tmpdir:
        orig_cwd = os.getcwd()
        os.chdir(tmpdir)
        try:
            yield
        finally:
            os.chdir(orig_cwd)

def TextIO(s=None, *, name):
    fp = io.BytesIO(s)
    fp.name = name
    return io.TextIOWrapper(fp, encoding='UTF-8')

def __run_main(argv, stdin):
    sys.argv = argv
    if stdin is not None:
        if isinstance(stdin, str):
            stdin = stdin.encode('UTF-8')
        sys.stdin = mock_stdin = TextIO(stdin, name=sys.__stdin__.name)
    else:
        mock_stdin = None
    sys.stdout = mock_stdout = TextIO(name=sys.__stdout__.name)
    sys.stderr = mock_stderr = TextIO(name=sys.__stderr__.name)
    import lib.cli
    try:
        lib.cli.main()
    except SystemExit as exc:
        if exc.code != 0:
            raise
    for fp in (sys.stdout, sys.stderr):
        fp.flush()
        s = fp.buffer.getvalue()  # pylint: disable=no-member
        yield s.decode('UTF-8')
    del mock_stdin, mock_stdout, mock_stderr

def _run_main(argv, stdin):
    # abuse mock to save&restore sys.argv, sys.stdin, etc.:
    with mock.patch.multiple(sys, argv=None, stdin=None, stdout=None, stderr=None):
        return tuple(__run_main(argv, stdin))

run_main = isolation(_run_main)

def t(*, stdin=None, files=None, stdout, stdout_ipa=None, stderr='', stderr_ipa=None):
    if stdout_ipa is None:
        stdout_ipa = stdout
    if stderr_ipa is None:
        stderr_ipa = stderr
    argv = ['anorack']
    if files is not None:
        for (name, content) in files:
            with open(name, 'wt', encoding='UTF-8') as file:
                file.write(content)
            argv += [name]
    (actual_stdout, actual_stderr) = run_main(argv, stdin)
    if '-@' in stdout:
        stdout = stdout.replace('-@', '@')
        actual_stdout = actual_stdout.replace('-@', '@')
    assert_equal(stdout, actual_stdout)
    assert_equal(stderr, actual_stderr)
    argv += ['--ipa']
    (actual_stdout, actual_stderr) = run_main(argv, stdin)
    actual_stderr = actual_stderr.replace('t͡ʃ', 'tʃ')
    assert_equal(stdout_ipa, actual_stdout)
    assert_equal(stderr_ipa, actual_stderr)

def test_stdin():
    t(
        stdin=(
            'It could be carried by an African swallow!\n'
            'Oh, yeah, a African swallow maybe, but not an\n'
            'European swallow.\n'
        ),
        stdout=(
            "<stdin>:2: a African -> an African /'afrIk@n/\n"
            "<stdin>:3: an European -> a European /j,U@r-@p'i@n/\n"
        ),
        stdout_ipa=(
            "<stdin>:2: a African -> an African /ˈafɹɪkən/\n"
            "<stdin>:3: an European -> a European /jˌʊəɹəpˈiən/\n"
        ),
    )

@tmpcwd()
def test_files():
    t(
        files=(
            ('holy', 'It could be carried by a African swallow!'),
            ('grail', 'Oh, yeah, an African swallow maybe, but not an European swallow.'),
        ),
        stdout=(
            "holy:1: a African -> an African /'afrIk@n/\n"
            "grail:1: an European -> a European /j,U@r-@p'i@n/\n"
        ),
        stdout_ipa=(
            "holy:1: a African -> an African /ˈafɹɪkən/\n"
            "grail:1: an European -> a European /jˌʊəɹəpˈiən/\n"
        ),
    )

def test_warning():
    def dummy_choose_art(phon):  # pylint: disable=unused-argument
        return NotImplemented
    with mock.patch('lib.cli.choose_art', dummy_choose_art):
        t(
            stdin='A scratch?!',
            stdout='',
            stderr="anorack: warning: can't determine correct article for 'scratch' /skr'atS/\n",
            stderr_ipa="anorack: warning: can't determine correct article for 'scratch' /skɹˈatʃ/\n",
        )

def test_changelog():
    argv = ['anorack', 'doc/changelog']
    (actual_stdout, actual_stderr) = run_main(argv, None)
    assert_equal('', actual_stdout)
    assert_equal('', actual_stderr)

def test_version():
    argv = ['anorack', '--version']
    (actual_stdout, actual_stderr) = run_main(argv, None)
    assert_not_equal('', actual_stdout)
    assert_equal('', actual_stderr)

# vim:ts=4 sts=4 sw=4 et
