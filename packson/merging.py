# -*- coding: utf-8 -*-

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from __future__ import unicode_literals

from six import StringIO

from nbdime.merging.generic import decide_merge_with_diff
from nbdime.merging.decisions import apply_decisions
from nbdime.diffing.generic import diff_dicts
from nbdime.utils import Strategies
from nbdime.prettyprint import (
    pretty_print_notebook_diff,
    pretty_print_merge_decisions,
    pretty_print_notebook,
    PrettyPrintConfig,
)

import nbdime.log
import nbdime.prettyprint

nbdime.prettyprint.notebook_diff_header = """\
jpdiff {afn} {bfn}
--- {afn}{atime}
+++ {bfn}{btime}
"""


def merge_strategies(args):
    strategies = Strategies(
        {
            # Pick highest minor format:
            "/version": "take-max"
        }
    )

    ignore_transients = args.ignore_transients if args else True
    if ignore_transients:
        strategies.transients = []
        strategies.update({})

    # Get args, default to inline for cli tool, intended to produce
    # an editable notebook that can be manually edited
    merge_strategy = args.merge_strategy if args else None

    # Set root strategy
    strategies["/"] = merge_strategy

    return strategies


def decide_merge(base, local, remote, args=None):
    # Build merge strategies for each document path from arguments
    strategies = merge_strategies(args)

    # Compute diffs
    local_diffs = diff_dicts(base, local)
    remote_diffs = diff_dicts(base, remote)

    # Debug outputs
    if args and args.log_level == "DEBUG":
        # log pretty-print config object:
        config = PrettyPrintConfig()

        nbdime.log.debug("In merge, base-local diff:")
        config.out = StringIO()
        pretty_print_notebook_diff("<base>", "<local>", base, local_diffs, config)
        nbdime.log.debug(config.out.getvalue())

        nbdime.log.debug("In merge, base-remote diff:")
        config.out = StringIO()
        pretty_print_notebook_diff("<base>", "<remote>", base, remote_diffs, config)
        nbdime.log.debug(config.out.getvalue())

    # Execute a generic merge operation
    decisions = decide_merge_with_diff(
        base, local, remote, local_diffs, remote_diffs, strategies
    )

    # Debug outputs
    if args and args.log_level == "DEBUG":
        nbdime.log.debug("In merge, decisions:")
        config.out = StringIO()
        pretty_print_merge_decisions(base, decisions, config)
        nbdime.log.debug(config.out.getvalue())

    return decisions


def merge(base, local, remote, args=None):
    """Merge changes introduced by notebooks local and remote from a shared ancestor base.

    Return new (partially) merged notebook and unapplied diffs from the local and remote side.
    """
    if args and args.log_level == "DEBUG":
        # log pretty-print config object:
        config = PrettyPrintConfig()
        for (name, nb) in [("base", base), ("local", local), ("remote", remote)]:
            nbdime.log.debug("In merge, input %s notebook:", name)
            config.out = StringIO()
            pretty_print_notebook(nb, config)
            nbdime.log.debug(config.out.getvalue())

    decisions = decide_merge(base, local, remote, args)

    merged = apply_decisions(base, decisions)

    if args and args.log_level == "DEBUG":
        nbdime.log.debug("In merge, merged notebook:")
        config.out = StringIO()
        pretty_print_notebook(merged, config)
        nbdime.log.debug(config.out.getvalue())
        nbdime.log.debug("End merge")

    return merged, decisions
