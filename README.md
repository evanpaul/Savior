# Savior
If your Reddit saved list is growing haphazardly, Savior can help (as long as you have Reddit Gold... it's a capitalistic superhero)

## User Guide
Note: this script requires Python 3; macOS comes preinstalled with Python 2.7. You can easily install python3 via homebrew: `brew install python3`
and then execute Python 3 code by preceding a .py file with "python3" e.g. `python3 savior.py --auth`. If you don't have homebrew, just search for downloading Python 3 for macOS, it isn't too difficult. Windows users won't have to worry about this unless they have installed multiple versions of Python, in which case follow the preceding advice. Linux users, you'll be fine.

As mentioned above, unfortunately this script also requires that your account is a Reddit Gold member.
### First time steps
1. Run `savior.py --auth`, read and accept the terms Reddit presents to you
2. Copy the authorization code from the resultant URL (http://localhost/?state=helloworld&code=[CODE])
3. Run savior.py --token [auth_code]. A refresh token will be saved to a file so you don't need to run these steps again unless the token is somehow deleted.

### Categorizing and sorting
1. Run `savior.py --subreddits` to generate a text file with a list of all the subreddits your account is subscribed to. At the moment, this script does not support saved posts from subreddits you are not subscribed to (due to Reddit API constraints)
2. Apply categories to each subreddit or leave some uncategorized. Simply add a space after the subreddits then type the category you wish to assign it to. Once you've done this you should save the file as a backup (in case you accidentally run `savior.py --subreddits` again and don't want your hard work to be overwritten)
3. Run `savior.py --sort` to fetch all of your saved posts and apply the supplied categories. Note: this will take a significant amount of time depending on the size of your saved list due to Reddit's API rate limiting. You should find something fun to do in the mean time.
