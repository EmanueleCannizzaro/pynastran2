#!/usr/bin/python
from __future__ import print_function
import sys
from pyNastran.bdf.bdf import BDF, to_fields, BDFCard, interpret_value
from pyNastran.bdf.cards.utils import wipe_empty_fields
import logging

logger = logging.getLogger("bdfuniq")
logger.setLevel(logging.DEBUG)

log_formater = logging.Formatter(
    fmt="%(name)-10s: %(levelname)-5s: %(message)s")

log_handler_stderr = logging.StreamHandler()
log_handler_stderr.setFormatter(log_formater)
logger.addHandler(log_handler_stderr)

log_handler_file = logging.FileHandler("bdf_get_uniq.log", "a")
log_handler_file.setFormatter(log_formater)
logger.addHandler(log_handler_file)

includeDir = None


class BDFuniqCard(BDF):
    def __init__(self, log, fingset):
        self.card_set = fingset
        #self.new_bdf = new_bdf
        BDF.__init__(self, log=log)

    #def _parse_executive_control_deck(self):
      #pass

    def cross_reference(self, xref):
        pass

    def add_card(self, card_lines, card_name, comment=''):
        card = to_fields(card_lines, card_name)
        card = [interpret_value(val) for val in card]
        card = BDFCard(card)

        #if card_name == "LOAD":
        rec = []
        for item in card:
            if isinstance(item, int):
                item = 1
            elif isinstance(item, float):
                item = 1.0
            rec.append(item)
            #print(type(c), c)
        #print("*", rec)
        rec_str = str(rec)
        if not rec_str in self.card_set:
            #self.newBDF.add_card(card, card_name, iCard, old_card_obj)
            #print(card)
            self.card_set.add(rec_str)

    def is_reject(self, card_name):
        """Can the card be read"""
        if card_name.startswith('='):
            return False
        elif not card_name in self.cards_to_read:
            if card_name:
                if card_name not in self.reject_count:
                    self.log.info("reject_card_name = %r" % card_name)
                    self.reject_count[card_name] = 0
                self.reject_count[card_name] += 1
        return False

    def write_bdf(self):
        with open('cards.out.bdf', 'wb') as bdf_file:
            for card in self.card_set:
                bdf_file.write(str(card) + '\n')
        print("please see cards.out.bdf")

def get_unique_bdf_cards():
    print("enter list of filenames at the command line...")
    card_fingerprint_set = set()
    infilenames = sys.argv[1:]
    assert len(infilenames) > 0, infilenames
    for infilename in infilenames:
        print("running infilename=%r" % infilename)
        try:
            infilename = infilename.strip()
            sys.stdout.flush()
            model = BDFuniqCard(log=logger,
                        fingset=card_fingerprint_set)
            model.read_bdf(infilename)
        except Exception as e:
            logger.error(e)
    model.write_bdf()
    print("done...")

if __name__ == '__main__':  # pragma: no cover
    get_unique_bdf_cards()