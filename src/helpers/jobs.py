import argparse
import random
from datetime import datetime
from typing import Union, List

from src import Task, BatchJob, Item, strip_prefix, console, Suggestion, ask_yes_no_question, TaskIds, \
    ScholarlyArticleItems, RiksdagenDocumentItems, ThesisItems, print_found_items_table, ask_add_to_job_queue, \
    print_best_practice, print_keep_an_eye_on_wdqs_lag, login, print_running_jobs, print_finished, add_to_job_pickle, \
    print_job_statistics, tasks


def process_qid_into_job(qid: str = None,
                         task: Task = None,
                         args: argparse.Namespace = None,
                         confirmation: bool = False) -> Union[BatchJob, None]:
    # logger = logging.getLogger(__name__)
    if qid is None:
        raise ValueError("qid was None")
    if args is None:
        raise ValueError("args was None")
    if task is None:
        raise ValueError("task was None")
    item = Item(
        id=strip_prefix(qid),
        task=task
    )
    if item.label is not None:
        console.print(f"Working on {item}")
        # generate suggestion with all we need
        suggestion = Suggestion(
            item=item,
            task=task,
            args=args
        )
        if confirmation:
            answer = ask_yes_no_question("Do you want to continue?")
            if not answer:
                return None
        with console.status(f'Fetching items with labels that have one of '
                            f'the search strings by running a total of '
                            f'{len(suggestion.search_strings) * task.number_of_queries_per_search_string} '
                            f'queries on WDQS...'):
            if task.id == TaskIds.SCHOLARLY_ARTICLES:
                items = ScholarlyArticleItems()
            elif task.id == TaskIds.RIKSDAGEN_DOCUMENTS:
                items = RiksdagenDocumentItems()
            elif task.id == TaskIds.THESIS:
                items = ThesisItems()
            else:
                raise ValueError(f"{task.id} was not recognized")
            items.fetch_based_on_label(suggestion=suggestion,
                                       task=task)
        if len(items.list) > 0:
            # Randomize the list
            items.random_shuffle_list()
            print_found_items_table(args=args,
                                    items=items)
            job = BatchJob(
                items=items,
                suggestion=suggestion
            )
            answer = ask_add_to_job_queue(job)
            if answer:
                return job
        else:
            console.print("No matching items found")
            return None
    else:
        console.print(f"Label for {task.language_code} was None on {item.url()}, skipping")


def process_user_supplied_qids_into_batch_jobs(args: argparse.Namespace = None,
                                               task: Task = None) -> List[BatchJob]:
    """Given a list of QIDs, we go through
    them and return a list of jobs"""
    # logger = logging.getLogger(__name__)
    if args is None:
        raise ValueError("args was None")
    if task is None:
        raise ValueError("task was None")
    print_best_practice(task)
    jobs = []
    for qid in args.add:
        job = process_qid_into_job(qid=qid,
                                   task=task,
                                   args=args)
        if job is not None:
            jobs.append(job)
    return jobs


def run_jobs(jobs: List[BatchJob] = None):
    if jobs is None:
        raise ValueError("jobs was None")
    print_keep_an_eye_on_wdqs_lag()
    login()
    print_running_jobs(jobs)
    count = 0
    start_time = datetime.now()
    for job in jobs:
        count += 1
        job.run(jobs=jobs, job_count=count)
    print_finished()
    end_time = datetime.now()
    console.print(f'Total runtime: {end_time - start_time}')


def handle_job_preparation_or_run_directly_if_any_jobs(args: argparse.Namespace = None,
                                                       jobs: List[BatchJob] = None):
    if len(jobs) > 0:
        if args.prepare_jobs:
            console.print(f"Adding {len(jobs)} job(s) to the jobs file")
            for job in jobs:
                add_to_job_pickle(job)
            print_job_statistics(jobs=jobs)
            console.print(f"You can run the jobs "
                          f"non-interactively e.g. on the Toolforge "
                          f"Kubernetes cluster using -r or --run-prepared-jobs. "
                          f"See https://phabricator.wikimedia.org/T285944 "
                          f"for details")
        else:
            run_jobs(jobs)


def get_validated_main_subjects_as_jobs(args: argparse.Namespace = None,
                                        main_subjects: List[str] = None,
                                        jobs: List[BatchJob] = None):
    """This function randomly picks a subject and present it for validation"""
    # logger = logging.getLogger(__name__)
    if jobs is None:
        raise ValueError("jobs was None")
    if not isinstance(jobs, List):
        raise ValueError("jobs was not a list")
    if args is None:
        raise ValueError("args was None")
    if main_subjects is None:
        raise ValueError("main subjects was None")
    # TODO implement better check for duplicates to avoid wasting resources
    picked_before = []
    while True:
        console.print(f"Picking a random main subject")
        qid = random.choice(main_subjects)
        if qid not in picked_before:
            job = process_qid_into_job(qid=qid,
                                       # The scientific article task is hardcoded for now
                                       task=tasks[0],
                                       args=args,
                                       confirmation=True)
            if job is not None:
                jobs.append(job)
                picked_before.append(qid)
            print_job_statistics(jobs=jobs)
            answer = ask_yes_no_question("Match one more?")
            if not answer:
                break
        else:
            console.print("Skipping already picked qid")
    return jobs