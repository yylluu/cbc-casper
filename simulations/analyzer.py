import statistics

import casper.utils as utils


class Analyzer:
    def __init__(self, simulation):
        self.simulation = simulation
        self.global_view = simulation.network.global_view

    def num_messages(self):
        return len(self.messages())

    def num_safe_messages(self):
        return len(self.safe_messages())

    def num_unsafe_messages(self):
        return len(self.unsafe_messages())

    def num_bivalent_messages(self):
        return len(self.bivalent_messages())

    def prop_safe_messages(self):
        return float(self.num_safe_messages()) / self.num_messages()

    def safe_to_tip_length(self):
        return self.global_view.estimate().height - self.safe_tip_height()

    def safe_tip_height(self):
        if self.safe_tip():
            return self.safe_tip().height
        # Not sure I'm happy with -1 here
        return -1

    def bivalent_message_depth(self):
        max_height = max(map(lambda m: m.height, self.bivalent_messages()))
        return max_height - self.safe_tip_height()

    def bivalent_message_branching_factor(self):
        to_check = set(self.bivalent_messages())
        if self.safe_tip():
            to_check.add(self.safe_tip())

        check = to_check.pop()
        branches = 0
        num_checked = 0
        while check:
            if check in self.global_view.children:
                branches += len(self.global_view.children[check])
                num_checked += 1
            if not to_check:
                break
            check = to_check.pop()

        if num_checked == 0:
            return 0
        return branches / num_checked

    def bivalent_message_branching_factor_estimate(self):
        ''' Estimate formula taken from
        http://ozark.hendrix.edu/~ferrer/courses/335/f11/lectures/effective-branching.html '''
        return self.num_bivalent_messages() ** (1 / float(self.bivalent_message_depth()))

    def safe_tip(self):
        safe_messages = self.safe_messages()
        if not safe_messages:
            return None
        return sorted(list(safe_messages), key=lambda m: m.height)[-1]
        # return self.global_view.last_finalized_block

    def messages(self):
        return self.global_view.messages

    def safe_messages(self):
        if not self.global_view.last_finalized_block:
            return set()

        return set(
            map(
                lambda link: link[0],
                utils.build_chain(self.global_view.last_finalized_block, None)
            )
        )

    def bivalent_messages(self):
        return self.messages() - self.safe_messages() - self.unsafe_messages()

    def unsafe_messages(self):
        potential = self.messages() - self.safe_messages()

        if not self.safe_tip():
            return set()

        return {
            message for message in potential
            if message.height <= self.safe_tip().height
        }

    def latency_to_finality(self):
        safe_messages = self.safe_messages()

        # This can kind of throw off data.
        # Really just shouldn't report anything if no finality
        # But I didn't want to handle the reprecussions of returning None or something
        if not safe_messages:
            return len(self.global_view.messages)

        individual_latency = [
            self.global_view.when_finalized[message] - self.global_view.when_added[message]
            for message in safe_messages
        ]

        return statistics.mean(individual_latency)

    def orphan_rate(self):
        num_unsafe_messages = self.num_unsafe_messages()
        num_safe_messages = self.num_safe_messages()
        if num_unsafe_messages + num_safe_messages == 0:
            return 0
        return float(num_unsafe_messages) / (num_unsafe_messages + num_safe_messages)
