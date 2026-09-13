---
name: markdown
repo: github/docs
ref: main
commit: 078b5832caa5cde591c2babb389ef447a0ef66eb
source_path: content/get-started/writing-on-github/editing-and-sharing-content-with-gists/creating-gists.md
title: Creating gists
version: 0.0.0
fetched_at: 2026-09-13
---
## About gists

Gists provide a simple way to share code snippets with others. Every gist is a Git repository, which means that it can be forked and cloned. If you are signed in to  when you create a gist, the gist will be associated with your account and you will see it in your list of gists when you navigate to your .

Gists can be public or secret. Public gists show up in , where people can browse new gists as they're created. They're also searchable, so you can use them if you'd like other people to find and see your work.

Secret gists don't show up in  and are not searchable unless you are logged in and are the author of the secret gist. Secret gists aren't private. If you send the URL of a secret gist to a friend, they'll be able to see it. However, if someone you don't know discovers the URL, they'll also be able to see your gist. If you need to keep your code away from prying eyes, you may want to [create a private repository](/repositories/creating-and-managing-repositories/creating-a-new-repository) instead.

For  and ,  automatically scans _secret gists_ for partner secrets and informs the relevant partner whenever one of their secrets is leaked. See [AUTOTITLE](/code-security/concepts/secret-security/secret-scanning-for-partners).

 However, a secret gist can be made public by editing the gist and updating the visibility to public.



If your site administrator has disabled private mode, you can also use anonymous gists, which can be public or secret.





You'll receive a notification when:
* You are the author of a gist.
* Someone mentions you in a gist.
* You subscribe to a gist, by clicking **Subscribe** at the top of any gist.

You can pin gists to your profile so other people can see them easily. For more information, see [AUTOTITLE](/account-and-profile/how-tos/profile-customization/pinning-items-to-your-profile).

You can discover public gists others have created by going to the  and clicking **All Gists**. This will take you to a page of all gists sorted and displayed by time of creation or update. You can also search gists by language with . Gist search uses the same search syntax as [code search](/search-github/searching-on-github/searching-code).

Since gists are Git repositories, you can view their full commit history, complete with diffs. You can also fork or clone gists. For more information, see [AUTOTITLE](/get-started/writing-on-github/editing-and-sharing-content-with-gists/forking-and-cloning-gists).

You can download a ZIP file of a gist by clicking the **Download ZIP** button at the top of the gist. You can embed a gist in any text field that supports JavaScript, such as a blog post. To get the embed code, click the clipboard icon next to the **Embed** URL of a gist. To embed a specific gist file, append the **Embed** URL with `?file=FILENAME`.



Gist supports mapping GeoJSON files. These maps are displayed in embedded gists, so you can easily share and embed maps. For more information, see [AUTOTITLE](/repositories/working-with-files/using-files/working-with-non-code-files#mapping-geojsontopojson-files-on-github).



## Creating a gist

Follow the steps below to create a gist.

> [!NOTE]
> You can also create a gist using the . For more information, see [`gh gist create`](https://cli.github.com/manual/gh_gist_create) in the  documentation.
>
> Alternatively, you can drag and drop a text file from your desktop directly into the editor.

1. Sign in to .
1. Navigate to your .
1. On the top right, click on the "+" icon to create new gist.
1. Optionally, in the "Gist description" field, type a description for your gist.
1. In the "Filename including extension" field, type a file name for your gist, including the file extensions.
1. In the file contents field, type the text of your gist.
1. Optionally, to create a public gist, click , then click **Create public gist**.

   ![Screenshot of the visibility dropdown menu for a new gist. Next to a button labeled "Create secret gist", a dropdown icon is outlined in dark orange.](/assets/images/help/gist/gist-visibility-drop-down.png)
1. Click **Create secret Gist** or **Create public gist**.
