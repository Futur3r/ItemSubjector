import logging
from typing import Dict, List

from pydantic import BaseModel
from wikibaseintegrator.wbi_helpers import execute_sparql_query  # type: ignore

from src.models.wikimedia.wikidata.item import Item
from src.models.wikimedia.wikidata.sparql_item import SparqlItem

logger = logging.getLogger(__name__)


class Query(BaseModel):
    results: Dict = {}
    search_string = ""
    query_string = ""
    items: List[Item] = []

    def parse_results(self) -> None:
        # console.print(self.results)
        for item_json in self.results["results"]["bindings"]:
            logging.debug(f"item_json:{item_json}")
            item = SparqlItem(**item_json)
            item.validate_qid_and_copy_label()
            if not item.is_in_blocklist():
                self.items.append(item)
            else:
                logger.info(f"{item.label} found in blocklist, skipping")

    def strip_bad_chars(self):
        # Note this has to match the cleaning done in the sparql query
        # We lowercase and remove common symbols
        # We replace like this to save CPU cycles see
        # https://stackoverflow.com/questions/3411771/best-way-to-replace-multiple-characters-in-a-string
        self.search_string = (
            self.search_string
            # Needed for matching backslashes e.g. "Dmel\CG5330" on Q29717230
            .replace("\\", "\\\\")
            # Needed for when labels contain apostrophe
            .replace("'", "\\'")
            .replace(",", "")
            .replace(":", "")
            .replace(";", "")
            .replace("(", "")
            .replace(")", "")
            .replace("[", "")
            .replace("]", "")
        )

    def execute(self):
        self.results = execute_sparql_query(self.query_string)

    def get_results(self):
        """Do everything needed to get the results"""
        self.strip_bad_chars()
        self.build_query()
        self.execute()
        self.parse_results()

    def build_query(self):
        pass

    def print_number_of_results(self):
        logging.info(
            f"Got {len(self.items)} items from "
            f"WDQS using the search string {self.search_string}"
        )
