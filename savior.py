import sys
import requests
import requests.auth
import datetime
import argparse
import time
from collections import defaultdict
import webbrowser
import getpass as gp


def get_readable_date(unix_epoch_time):
    return datetime.datetime.fromtimestamp(
        float(unix_epoch_time)).strftime('%c')


def refresh_token():
    try:
        with open("refresh.token", "r") as f:
            refresh_token = f.read()
    except FileNotFoundError:
        sys.exit("[ERR] No refresh token found! Please run savior.py --token <auth_code> to get an access token " +
                 "or savior.py --auth to get an authorization code")

    client_auth = requests.auth.HTTPBasicAuth(SAVIOR["id"], SAVIOR["secret"])
    headers = {"User-Agent": SAVIOR["user-agent"]}
    post_data = {"grant_type": "refresh_token", "refresh_token": refresh_token}
    response = requests.post("https://www.reddit.com/api/v1/access_token",
                             auth=client_auth, data=post_data, headers=headers)

    if response.status_code != 200:
        sys.exit("[ERR] Refreshing access token failed :(")
    else:
        print("[!] Successfully refreshed access token")
        return response.json()["access_token"]


def get_user_name():
    try:
        with open("user.txt", "r") as f:
            user = f.read()
    except FileNotFoundError:
        user = input(
            "Enter Reddit account username (this will be stored to a file for convenience): ")
        with open("user.txt", "w") as f:
            f.write(user)
    return user

def get_token(auth_code):
    # Get user info
    SAVIOR["username"] = get_user_name()
    SAVIOR["password"] = gp.getpass(
        "Enter password (this will not be saved): ").strip()
    # Request info
    headers = {"User-Agent": SAVIOR["user-agent"]}
    client_auth = requests.auth.HTTPBasicAuth(SAVIOR["id"], SAVIOR["secret"])
    post_data = {"grant_type": "authorization_code",
                 "code": auth_code,
                 "redirect_uri": "http://localhost",
                 "username": SAVIOR["username"],
                 "password": SAVIOR["password"]}

    response = requests.post("https://www.reddit.com/api/v1/access_token",
                             auth=client_auth, data=post_data, headers=headers)

    if response.status_code == 200:
        r = response.json()
        if "access_token" in r and "refresh_token" in r:
            with open("refresh.token", "w") as f:
                f.write(r["refresh_token"])

            print("[!] Access token successfully acquired (expires in 1 hour)!")
            sys.exit("[!] Run savior.py --subreddits")

        else:
            sys.exit(response.json())

    else:
        sys.exit(str(response.status_code))


def get_subreddits():
    token = refresh_token()
    headers = {"Authorization": "bearer " +
               token, "User-Agent": SAVIOR["user-agent"]}

    response = requests.get(
        "https://oauth.reddit.com/subreddits/mine/subscriber?limit=%d" % BATCH_SIZE, headers=headers)

    if response.status_code == 200:
        data = response.json()["data"]
        sorted_subs = []
        # Collect and sort subreddit names
        for subreddit in data["children"]:
            sorted_subs.append(subreddit["data"]["display_name"])
        sorted_subs.sort()

        # Write subreddit names to file
        with open("subreddits.txt", "w") as f:
            for subreddit in sorted_subs:
                f.write(subreddit + "\n")
        print("[!] Recorded %d subreddits to subreddits.txt" %
              len(data["children"]))
        print("[!] Add categories after each subreddit before sorting. Subreddits without categories will be ignored!")
        print("[!] Example:")
        print("programming coding")
        print("dailyprogrammer coding")
        print("aww doggos")
        print("gaming")
        print("awwducational doggos")
        print("[!] Once you've assigned categories, run savior.py --sort")
        print("[!] Consider saving a copy of your modified subreddits.txt so that you don't have to recategorize in the future")

    else:
        sys.exit(str(response.status_code))


def sort_saved_posts():
    SAVIOR["username"] = get_user_name()
    token = refresh_token()
    sub_cat = {}
    cat_sub = defaultdict(list)
    try:
        edit_flag = False
        with open("subreddits.txt", "r") as f:
            lines = f.read().split("\n")
            for line in lines:
                lsplit = line.split(" ")

                if len(lsplit) == 2:
                    edit_flag = True
                    sub = lsplit[0]
                    category = lsplit[1]
                    sub_cat[sub] = category
                    # Assign subreddit to user-specified category
                    cat_sub[category].append(sub)

        if not edit_flag:
            print(
                "[!] It appears that you didn't apply categories to to any subreddits in subreddits.txt")
            sys.exit(
                "[!] Format per line: [subreddit name] [category name (optional)]")
    except FileNotFoundError:
        sys.exit(
            "[!] subreddits.txt not found! Please run savior.py --subreddits before sorting")

    headers = {"Authorization": "bearer " +
               token, "User-Agent": SAVIOR["user-agent"]}

    num_cat = len(cat_sub.keys())
    post_count = 0
    next_batch_ptr = None
    sub_post_counter = defaultdict(int)
    current_cat = next(iter(cat_sub))
    current_sub = cat_sub[current_cat][0]
    saved_posts = set()
    # The sr parameter is actually not documented by Reddit, but available in some source code.
    # This means that this script is inherently a little hacky and could break at the whim of Reddit Devs.
    response = requests.get(('https://oauth.reddit.com/user/%s/saved?limit=%d?sr=%s') %
                            (SAVIOR["username"], BATCH_SIZE, current_sub), headers=headers)

    # Sift through saved posts category by category, subreddit by subreddit
    while cat_sub.keys():
        # The first response object doesn't include this key
        if not "x-ratelimit-remaining" in response.headers or float(response.headers["x-ratelimit-remaining"]) > 1:
            if response.status_code == 200:
                data = response.json()["data"]
                next_batch_ptr = data["after"]

                for post in data["children"]:
                    post_count += 1
                    subreddit = post["data"]["subreddit"]
                    post_id = "t3_" + post["data"]["id"]
                    date = post["data"]["created"]
                    # Convert unix epoch time to human readable
                    readable_date = get_readable_date(date)

                    if subreddit in sub_cat:
                        print("[%s] (%s)\t%s => %s" % (
                            post_id, readable_date, subreddit, sub_cat[subreddit]))
                        s = SavedPost(post_id, subreddit,
                                      date, sub_cat[subreddit])
                    else:
                        print("[%s] (%s)\t%s" %
                              (post_id, readable_date, subreddit))
                        s = SavedPost(post_id, subreddit, date)
                    # REVIEW Why are posts appearing twice ??
                    saved_posts.add(s)
                    # Count posts saved per subreddit
                    sub_post_counter[subreddit] += 1
            else:
                sys.exit(str(response.status_code))
            # End of posts
            if next_batch_ptr == None:
                cat_sub[current_cat].remove(current_sub)
                # If we've already exhausted the subreddits for this category, delete it and move on
                if not cat_sub[current_cat]:
                    del cat_sub[current_cat]

                    if cat_sub.keys():
                        current_cat = next(iter(cat_sub))
                    else:
                        break
                current_sub = cat_sub[current_cat][0]

            response = requests.get(
                ('https://oauth.reddit.com/user/%s/saved?limit=%d&count=%d&after=%s&sr=%s') %
                (SAVIOR["username"], BATCH_SIZE, post_count, next_batch_ptr, current_sub), headers=headers)
        else:
            print("[WARNING] Rate limit reached, taking a 10 minute nap...")
            time.sleep(600)

    # Posts are sorted from oldest to newest
    # This ensures that when we iterate and POST new saves, the result will be from newest to oldest
    sorted_posts = sorted(saved_posts, key=lambda post: post.date)

    print("[!] Updating saved list...")
    print("[!] This will take at least %d minutes due to Reddit's rate limiting" % (
        len(sorted_posts) / 60))
    failed_requests = []
    # Save newly categorized posts
    for sp in sorted_posts:
        time.sleep(1)
        if sp.category:
            post_data = {"id": sp.post_id, "category": sp.category}
        else:
            post_data = {"id": sp.post_id}

        response = requests.post(
            "https://oauth.reddit.com/api/save", data=post_data, headers=headers)

        if response.status_code != 200:
            if response.status_code == 401:
                print(
                    "[WARNING] 401 Credentials timed out, attempting to refresh acess token...")
                token = refresh_token()
                # Update headers with new access token and place post back at the front of the queue
                headers = {"Authorization": "bearer " +
                           token, "User-Agent": SAVIOR["user-agent"]}
                sorted_posts.insert(0, sp)
            elif response.status_code == 400:
                # print("[ERR] 400 Invalid request:")
                # print(post_data)
                # print(headers)
                # print(get_readable_date(sp.date))
                failed_requests.append(sp)
            else:
                sys.exit("[ERR] Failed with unexpected error code:",
                         response.status_code)

        if "x-ratelimit-remaining" in response.headers and float(response.headers["x-ratelimit-remaining"]) <= 1.0:
            print("[WARNING] Rate limit reached, taking a 10 minute nap...")
            time.sleep(600)
    # REVIEW Why did these posts fail? They don't seem to exist.
    # I can't access these by manually putting the IDs into my address bar
    # I suspect the posts have been deleted, but for some reason remain in saved list.

    # TODO Test if this would even work.
    # print("[!] Unsaving the following %d posts due to errors" %
    #       len(failed_requests))
    # if len(failed_requests) > 50:
    #     sys.exit("[DEBUG] Woah, that's a lot of failures. Let's not.")
    # # Unsave unruly (?) posts
    # for esp in failed_requests:
    #     time.sleep(1)
    #     post_data = {"id": esp.post_id}
    #     response = requests.post(
    #         "https://oauth.reddit.com/api/unsave", data=post_data, headers=headers)
    #     if response.status_code != 200:
    #         print("[WARNING] Failed unsaving a post we were unable to save... yikes.")
    #     else:
    #         print(esp.post_id, esp.date, esp.subreddit)
    #     if "x-ratelimit-remaining" in response.headers and float(response.headers["x-ratelimit-remaining"]) <= 1.0:
    #         print("[WARNING] Rate limit reached, taking a 10 minute nap...")
    #         time.sleep(600)

    print("[!] Sorted %d saved posts into %d categories" %
          (post_count, num_cat))
    print("[!] Encountered %d errors" % len(failed_requests))


class SavedPost:
    def __init__(self, post_id, subreddit, date, category=None):
        self.post_id = post_id
        self.subreddit = subreddit
        self.date = date
        self.category = category

    def __eq__(x, y):
        return x.post_id == y.post_id

    def __hash__(self):
        return hash(self.post_id)


if __name__ == "__main__":
    # Low priority:
    # TODO Maybe force user to rename file to "categorized.txt" so that they don't accidentally overwrite?
    # TODO Add progress bar to POSTing saves
    # TODO Create simple HTML page and webserver to make grabbing code from URL more user-friendly
    # TODO Automate auth -> token acquisition process
    SAVIOR = {
        "secret": "aGzfQDOBY5YRjsIUPErzxhyK9U4",
        "id": "dT0eSuUwrZGdNw",
        'user-agent': 'python:savior:v1.0.0 (by /u/The7DeadlySyns)'
    }

    # Parse arguments to determine mode
    parser = argparse.ArgumentParser(
        description='Sort a Redditor\'s saved list')
    parser.add_argument('--auth', action="store_true")
    parser.add_argument('--token', dest="acquire_token")
    parser.add_argument('--subreddits', action="store_true")
    parser.add_argument('--sort', action="store_true")
    args = parser.parse_args()

    # REVIEW Interesting and annoying edge case: if the token starts with a '-' (yes this really can happen)
    # Only allow for one mode at a time
    if not (args.auth ^ bool(args.acquire_token) ^ args.subreddits ^ args.sort):
        sys.exit(
            "[usage] python savior.py --{auth, token <auth_code>, subreddits, sort}")

    BATCH_SIZE = 100  # Maximum allowed by API

    # Get authorization code
    if args.auth:
        webbrowser.open("https://www.reddit.com/api/v1/authorize?client_id=" + SAVIOR["id"] +
                        "&response_type=code&state=helloworld&redirect_uri=http://localhost&duration=permanent&scope=save history mysubreddits")
        print("[!] Please copy the authorization code from the URL (http://localhost/?state=helloworld&code=<CODE>)")
        print("[!] Run savior.py --token <auth_code> to receive an API access token (you only need to do this once)")
    # Get access token
    elif bool(args.acquire_token):
        get_token(args.acquire_token)
    # REVIEW Can we do anything about posts that are from unsubscribed subreddits? Maybe
    elif args.subreddits:
        get_subreddits()
    elif args.sort:
        sort_saved_posts()
