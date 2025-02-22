"""
Edit the source code of Sage interactively

AUTHORS:

- Nils Bruin
- William Stein -- touch up for inclusion in Sage.
- Simon King: Make it usable on extension classes that do not have
  a docstring; include this module into the reference manual and
  fix some syntax errors in the doc strings.

This module provides a routine to open the source file of a python
object in an editor of your choice, if the source file can be figured
out.  For files that appear to be from the sage library, the path name
gets modified to the corresponding file in the current branch, i.e.,
the file that gets copied into the library upon 'sage -br'.

The editor to be run, and the way it should be called to open the
requested file at the right line number, can be supplied via a
template. For a limited number of editors, templates are already known
to the system. In those cases it suffices to give the editor name.

In fact, if the environment variable :envvar:`EDITOR` is set to a known editor,
then the system will use that if no template has been set explicitly.
"""
# ****************************************************************************
#       Copyright (C) 2007 Nils Bruin <nbruin@sfu.ca> and
#                          William Stein <wstein@math.ucsd.edu>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#                  https://www.gnu.org/licenses/
# ****************************************************************************

import sage.misc.sageinspect
import os
import re

from string import Template

# by default we do not have an edit template
edit_template = None

# we can set some defaults, however. Add your own if you like.

template_defaults = {
      'vi'       : Template('vi -c ${line} ${file}'),
      'vim'      : Template('vim -c ${line} ${file}'),
      'emacs'    : Template('emacs ${opts} +${line} ${file}'),
      'nedit-nc' : Template('nedit-nc -line ${line} ${file}'),
      'nedit-client' : Template('nedit-client -line ${line} ${file}'),
      'ncl'      : Template('ncl -line ${line} ${file}'),
      'gedit'    : Template('gedit +${line} ${file} &'),
      'kate'     : Template('kate -u --line +${line} ${file} &')   }


def file_and_line(obj):
    r"""
    Look up source file and line number of ``obj``.

    If the file lies in the Sage library, the path name of the
    corresponding file in the current branch (i.e., the file that gets
    copied into the Sage library upon running 'sage -br').  Note that
    the first line of a file is considered to be 1 rather than 0
    because most editors think that this is the case.

    AUTHORS:

    - Nils Bruin (2007-10-03)
    - Simon King (2011-05): Use :mod:`~sage.misc.sageinspect` to get the file
      and the line.

    EXAMPLES::

        sage: import sage.misc.edit_module as edit_module
        sage: edit_module.file_and_line(sage.cpython)
        ('...sage/cpython/__init__.py', 0)

    The following tests against a bug that was fixed in :trac:`11298`::

        sage: edit_module.file_and_line(x)                                              # needs sage.symbolic
        ('...sage/symbolic/expression...pyx', ...)
    """
    # d = inspect.getdoc(obj)
    # ret = sage.misc.sageinspect._extract_embedded_position(d);
    # if ret is not None:
    #     (_, filename, lineno) = ret
    # else:
    #     filename = inspect.getsourcefile(obj)
    #     _,lineno = inspect.findsource(obj)

    #
    #  for sage files, the registered source file is the result of the
    #  preparsing these files end in ".py" and have "*autogenerated*"
    #  on the second line for those files, we replace the extension by
    #  ".sage" and we subtract 3 from the line number to compensate
    #  for the 3 lines that were prefixed in the preparsing process
    #
    from sage.misc.sageinspect import sage_getfile, sage_getsourcelines
    filename = sage_getfile(obj)
    lineno = sage_getsourcelines(obj)[1] - 1
    if filename.endswith('.py'):
        infile = open(filename, 'r')
        infile.readline()
        if infile.readline().find("*autogenerated*") >= 0:
            filename = filename[:-3] + '.sage'
            lineno -= 3

    runpathpattern = '^' + sage.env.SAGE_LIB
    develbranch = sage.env.SAGE_SRC
    filename = re.sub(runpathpattern, develbranch, filename)

    return filename, lineno + 1


def template_fields(template):
    r"""
    Given a String.Template object, returns the fields.

    AUTHOR:

    Nils Bruin (2007-10-22)

    EXAMPLES::

        sage: from sage.misc.edit_module import template_fields
        sage: from string import Template
        sage: t = Template("Template ${one} with ${two} and ${three}")
        sage: sorted(template_fields(t))
        ['one', 'three', 'two']
    """
    dict = {}
    dummy = None
    while not dummy:
        try:
            dummy = template.substitute(dict)
        except KeyError as inst:
            dict[inst.args[0]] = None
    return list(dict)

# The routine set_edit_template should only do some consistency
# checks on template_string It should not do any magic. This routine
# should give the user full control over what is going on.


def set_edit_template(template_string):
    r"""
    Set the default edit template string.

    It should reference ``${file}`` and ``${line}``. This routine normally
    needs to be called prior to using 'edit'. However, if the editor
    set in the shell variable :envvar:`EDITOR` is known, then the system will
    substitute an appropriate template for you. See
    edit_module.template_defaults for the recognised templates.

    AUTHOR:

    Nils Bruin (2007-10-03)

    EXAMPLES::

        sage: from sage.misc.edit_module import set_edit_template
        sage: set_edit_template("echo EDIT ${file}:${line}")
        sage: edit(sage)      # not tested
        EDIT /usr/local/sage/src/sage/__init__.py:1
    """
    global edit_template

    if not isinstance(template_string, Template):
        template_string = Template(template_string)
    fields = set(template_fields(template_string))
    if not (fields <= set(['file', 'line']) and ('file' in fields)):
        raise ValueError("Only ${file} and ${line} are allowed as template variables, and ${file} must occur.")
    edit_template = template_string

# The routine set_editor is for convenience and hence is allowed to
# apply magic. Given an editor name and possibly some options, it
# should try to set an editor_template that is as appropriate as
# possible for the situation. If it's necessary to query the
# environment for 'DISPLAY' to figure out if certain editors should
# be run in the background, this is where the magic should go.


def set_editor(editor_name, opts=''):
    r"""
    Set the editor to be used by the edit command by basic editor name.

    Currently, the system only knows appropriate call strings for a
    limited number of editors. If you want to use another editor, you
    should set the whole edit template via :func:`set_edit_template`.

    AUTHOR:

    Nils Bruin (2007-10-05)

    EXAMPLES::

        sage: from sage.misc.edit_module import set_editor
        sage: set_editor('vi')
        sage: sage.misc.edit_module.edit_template.template
        'vi -c ${line} ${file}'
    """
    if editor_name in sage.misc.edit_module.template_defaults:
        set_edit_template(Template(template_defaults[editor_name].safe_substitute(opts=opts)))
    else:
        raise ValueError("editor_name not known. Try set_edit_template(<template_string>) instead.")


def edit(obj, editor=None, bg=None):
    r"""nodetex
    Open source code of ``obj`` in editor of your choice.

    INPUT:

    - editor -- str (default: None); If given, use specified editor.
      Choice is stored for next time.

    AUTHOR:

    Nils Bruin (2007-10-03)

    EXAMPLES:

    This is a typical example of how to use this routine::

        # make some object obj
        sage: edit(obj)    # not tested

    Now for more details and customization::

        sage: import sage.misc.edit_module as m
        sage: m.set_edit_template("vi -c ${line} ${file}")

    In fact, since ``vi`` is a well-known editor, you could also just use::

        sage: m.set_editor("vi")

    To illustrate::

        sage: m.edit_template.template
        'vi -c ${line} ${file}'

    And if your environment variable :envvar:`EDITOR` is set to a recognised
    editor, you would not have to set anything.

    To edit the source of an object, just type something like::

        sage: edit(edit)           # not tested
    """
    global edit_template

    if editor:
        set_editor(editor)
    elif not edit_template:
        try:
            ED = os.environ['EDITOR']
            EDITOR = ED.split()
            base = EDITOR[0]
            opts = ' '.join(EDITOR[1:])   # for future use
            set_editor(base, opts=opts)
        except (ValueError, KeyError, IndexError):
            raise ValueError("Use set_edit_template(<template_string>) to set a default")

    if not edit_template:
        raise ValueError("Use set_edit_template(<template_string>) to set a default")

    filename, lineno = file_and_line(obj)
    cmd = edit_template.substitute(line=lineno, file=filename)

    if bg is True and cmd[-1] != '&':
        cmd = cmd + '&'
    if bg is False and cmd[-1] == '&':
        cmd = cmd[:-1]

    os.system(cmd)


def edit_devel(self, filename, linenum):
    """
    This function is for internal use and is called by IPython when you use
    the IPython commands ``%edit`` or ``%ed``.

    This hook calls the default implementation, but changes the filename for
    files that appear to be from the sage library: if the filename begins with
    'SAGE_LOCAL/lib/python.../site-packages', it replaces this by
    'SAGE_ROOT/src'.

    EXAMPLES::

        sage: %edit gcd         # indirect doctest, not tested
        sage: %ed gcd           # indirect doctest, not tested

    The above should open your favorite editor (as stored in the environment
    variable :envvar:`EDITOR`) with the file in which gcd is defined, and when your
    editor supports it, also at the line in which gcd is defined.
    """
    import IPython.core.hooks
    runpathpattern = '^' + sage.env.SAGE_LIB
    develbranch = sage.env.SAGE_SRC
    filename = re.sub(runpathpattern, develbranch, filename)
    IPython.core.hooks.editor(self, filename, linenum)
