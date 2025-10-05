OpenAI_Interaction

This is a continuation of the project "Persistent Assistant", the last chat has become extremely sluggish on Microsoft Edge
We have a single source of truth plan at project_plan_v3.yaml. In your scripts you can always ask for the next step in the plan using "python tools\show_next_step.py"
To maximize discipline and minimise drift We are in the process of maximising key project data other than code as schema enforced .yaml files.
We need to implement methods which write the yaml files as schema compliant, correcting where incorrect and ensuring new entries to the files conform.
We are in the process of creating a schema for the communications from persistent assistant to ai, and another for communication from ai to persistent assistant. This will help identify any drift.
We are collaborating on OS: Windows + PowerShell (no heredocs, no python - << 'PY').
Project: PersistentAssistant; packs always under tmp\feedback\pack_*.zip.
Local Exec Bridge: running on 127.0.0.1:8765 (Flask dev), works.
Phone preview: Flask dev on host: 0.0.0.0, default port 8770.
Approvals: file-drop JSON under tmp\phone\approvals\approve_*.json (listener active).
Guard: forbidden patterns in warn-but-continue preflight.
We have developed a load of tools for looking at the structure and architecture of any development project. 
We have so many tools I cannot remember them all. We need to keep a library of tools which can be used. Rewriting similar tools is inefficient and needs to be avoided at all costs.
In structure_sync.py there is a routine to create the project snapshot run_snapshot(root: Path, out_yaml: Path, out_md: Path, preview_lines: int = 10) -> Dict[str, Any]:
We need a schema modification section in the interaction schemas, and a strict process which always checks if a schema needs updating due to a suggestion. This will help us be more rtobust and develop more efficient methods. 
We must always learn from our failures and implement a change to improve robsustness.


We dont generally interact by me downloading anything from you, but if this became an efficient method I would consider it on rare occasions. 
Persistent Assistant send information to you in conforming to a schema which has been agreed. It can be adapted but is designed to give you all the relevant information to make clear decisions. It will include the ciurrent plan, the current proct structure, including a list of all the tool and their calling format so you will check if a tool already exists to do a task preventing rewriting due to amnesia.
The normal method for response is you create a script within the agreed communications schema which I cut and paste into the terminal window of vscode. 
I then return anything you ask for, again within the schema, but generally everything you need gets packed into the pack file.
I will not normally download anything just copy your commands as a package to be run on the local computer. 
send me one script to run, try to make it as robust as possible, ensure it doesn't block subsequent independent operations you want run if any operations fail, but obviously abort operations which are dependent, and generate you response pack that I can send to you to get all the info you need to decide on the next progress steps.
If we deviate from this plan then we must update the plan and then keep on track.
when scrolling back through interactions I have to scroll to the top in order to see the title of the script, and if the title is not unique then I have to read the previous interaction to check I am reading the correct one, so they should all be unique, referencing the plan step we are working on, and the version of the script if we have small issues like in this last script so the majority of the code will likely remain, just a syntax or other small error difference, but if you could put the title at the end of the script as well as at the top it would save me quite a bit of scrolling.
Our target is that my pc interacts with you directly, I only get involved in checking progress of the previous stage as reported by you in a brief summary, reading the list of up to 3 or 4 recommendations for the next step and letting you know if I have any queries, questions, suggestions or just respond with the number associated with the next tasks I select. 
We created a schema for this interaction but it hasn't been fully implemented yet. 
I am always keen on advanced diagnostics for debugging issues, but with the diagnostics being able to be switched off once debugging has been completed.
Do you have any further questions for me at this stage on what we are doing, why we are doing it, or suggestions on how we can maximize efficiency of this semi_automated project development tool, which has self introspection and polices its own capabilities against latest and greatest technology developments in the world of ai and professional software, editing its own code to achieve the best possible project development tools as the world of AI progresses.
