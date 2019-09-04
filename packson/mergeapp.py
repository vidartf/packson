# coding: utf-8

# Copyright (c) IPython Development Team.
# Distributed under the terms of the Modified BSD License.

from collections import OrderedDict
import io
import json
import os
import sys

from nbdime.args import ConfigBackedParser, Path, prettyprint_config_from_args
from nbdime.log import logger
from nbdime.prettyprint import pretty_print_merge_decisions
from nbdime.utils import EXPLICIT_MISSING_FILE, setup_std_streams

from .detect import detect
from .merging import merge

_description = ('Merge two npm package.json files "local" and "remote" with a '
                'common ancestor "base". If base is left out, it uses an '
                'empty notebook as the base.')


def read_package_json(filename):
    if filename == EXPLICIT_MISSING_FILE:
        return {}
    with io.open(filename, "r", encoding="utf8") as f:
        return json.load(f, object_pairs_hook=OrderedDict)


def detect_formatting(filename):
    if filename == EXPLICIT_MISSING_FILE:
        return None
    with io.open(filename, "r", encoding="utf8") as f:
        content = f.read()
        content.trim()


def main_merge(args):
    bfn = args.base
    lfn = args.local
    rfn = args.remote
    mfn = args.out

    from nbdime.args import process_diff_flags

    process_diff_flags(args)

    for fn in (bfn, lfn, rfn):
        if not os.path.exists(fn) and fn != EXPLICIT_MISSING_FILE:
            logger.error("Cannot find file '%s'", fn)
            return 1

    if lfn == rfn == EXPLICIT_MISSING_FILE:
        # Deleted both locally and remotely
        # Special case not well solved by routines below
        _handle_agreed_deletion(bfn, mfn, args)
        # Agreed on deletion = no conflics = return 0
        return 0

    formatting = detect(bfn) or detect(lfn) or detect(rfn)

    b = read_package_json(bfn)
    l = read_package_json(lfn)
    r = read_package_json(rfn)

    merged, decisions = merge(b, l, r, args)
    conflicted = [d for d in decisions if d.conflict]

    returncode = 1 if conflicted else 0

    if conflicted:
        logger.warning("Conflicts occured during merge operation.")
    else:
        logger.debug("Merge completed successfully with no unresolvable conflicts.")

    if args.decisions:
        # Print merge decisions (including unconflicted)
        config = prettyprint_config_from_args(args, out=io.StringIO())
        pretty_print_merge_decisions(b, decisions, config=config)
        logger.warning("Decisions:\n%s", config.out.getvalue())
    elif mfn:
        # Write partial or fully completed merge to given foo.ipynb filename
        with io.open(mfn, "w", encoding="utf8", newline=formatting.newline) as f:
            json.dump(merged, f, indent=formatting.indent)
            f.write(formatting.newline)
        logger.info("Merge result written to %s", mfn)
    else:
        # Write merged notebook to terminal
        json.dump(merged, sys.stdout)
    return returncode


def _handle_agreed_deletion(base_fn, output_fn, args=None):
    """Handle merge when file has been deleted both locally and remotely"""
    assert base_fn != EXPLICIT_MISSING_FILE, (
        "sanity check failed: cannot have agreed decision on base %r" % base_fn
    )
    b = read_package_json(base_fn)
    if args and args.decisions:
        # Print merge decision (delete all)
        from nbdime.diffing.notebooks import diff_notebooks
        from nbdime.merging.decisions import MergeDecisionBuilder

        # Build diff for deleting all content:
        diff = diff_notebooks(b, {})
        # Make agreed decision from diff:
        bld = MergeDecisionBuilder()
        bld.agreement([], local_diff=diff, remote_diff=diff)
        decisions = bld.validated(b)
        # Print decition
        config = prettyprint_config_from_args(args, out=io.StringIO())
        pretty_print_merge_decisions(b, decisions, config=config)
        logger.warning("Decisions:\n%s", config.out.getvalue())

    elif output_fn:
        # Delete file if existing, if not do nothing
        if os.path.exists(output_fn):
            os.remove(output_fn)
            logger.info("Output file deleted: %s", output_fn)


def _build_arg_parser():
    """Creates an argument parser for the nbdiff command."""
    parser = ConfigBackedParser(description=_description, add_help=True)
    from nbdime.args import (
        add_generic_args,
        add_diff_args,
        add_merge_args,
        filename_help,
        add_filename_args,
        add_prettyprint_args,
    )

    add_generic_args(parser)
    add_diff_args(parser)
    add_merge_args(parser)
    add_prettyprint_args(parser)

    parser.add_argument(
        "base",
        type=Path,
        help=filename_help["base"],
        nargs="?",
        default=EXPLICIT_MISSING_FILE,
    )
    add_filename_args(parser, ["local", "remote"])

    parser.add_argument(
        "--out",
        default=None,
        type=Path,
        help="if supplied, the merged notebook is written "
        "to this file. Otherwise it is printed to the "
        "terminal.",
    )
    parser.add_argument(
        "--decisions",
        action="store_true",
        help="print a human-readable summary of conflicted "
        "merge decisions instead of merging the notebook.",
    )

    return parser


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    setup_std_streams()
    arguments = _build_arg_parser().parse_args(args)
    return main_merge(arguments)


if __name__ == "__main__":
    sys.exit(main())