# GitBoy command timing

Each button click creates a GitHub Issue. A workflow reads Issue commands in order and publishes a new screenshot to the profile. This is not real-time gameplay. Processing often takes tens of seconds, and queues, GitHub Actions availability and CDN caching may add extra delay.

**After you click Create / Submit new issue, the screen does not update immediately.** The command goes into the GitHub Actions queue, runs inside the emulator, saves the shared state and publishes a new screenshot. This often takes 15–30 seconds, but can take longer. Return to the profile and refresh after processing. There is no artificial cooldown between commands from the same account. Each GitHub Issue still takes time to launch a runner and publish an updated screenshot.

If the screen is temporarily unchanged, your command may have been ignored by the game itself, or another visitor may have played afterward. Look at the latest command and community leaderboard on the profile.
