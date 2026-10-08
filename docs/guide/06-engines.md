# To choose an AI engine

Glacier uses the **Codex plan** by default. You can choose another ready engine in **Settings** > **Models**. Available subscription CLIs depend on what is installed and signed in on this computer. Choose an installed local model there to keep its work on this computer; local models handle one task at a time.

## To use an API engine

Choose **OpenAI-compatible API** or **Anthropic API** in **Settings** > **Models**. Save your own API key in **Settings** > **Secrets**, then select its name in the engine settings. Enter a monthly spending cap and the model details. Glacier shows the month's spend and stops using that API engine when the cap is reached. It will not use an API engine until you select and configure it.

## What an engine can see

Every engine gets the same basic information about Glacier, its screens and controls, and the current system state. It also gets relevant memory notes and your saved preferences note when available.

In **Settings** > **Models**, turn **Remember previous chats** on or off to control whether earlier chats can be included. Chat context is redacted before it is sent. Notes and chats are treated as information, not instructions. The amount of context can vary with the model.

Changing the engine affects future replies. It does not change your saved chats or notes.
