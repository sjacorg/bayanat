# Workflow

SJAC's analysts follow a strict workflow for the analysis of Actors and Bulletins. The workflow is enforced in Bayanat's UI and can only be overridden by an administrator.

This workflow serves as a project management tool within Bayanat. It allows users to filter the data by its status and provides useful insights into the team's progress.

SJAC's workflow and the statuses are shipped in Bayanat by default, but other users can add or remove status and make changes to this flow.

## Flowchart
The following chart describes the workflow designed by SJAC for its data analysis process:

<br>

```mermaid
%%{ init: { 'flowchart': { 'curve': 'basis' } } }%%
graph TB

	subgraph 0 [Initial Status]
		A(Machine Created)
		B(Human Created)
  end

	subgraph 1 [Analysis]
  	A & B --> C[Assigned to user by admin]
    C --> D(Assigned)
    D --> DD[Updated by assignee]
    DD --> E(Updated)
    E --> F(Many times as required)
    E -.-> EE[Updated by senior]
    D -.-> EE
    EE --> EZ(Senior Updated)
    F --> E
  end

  E -.-> G[Assigned to reviewer by admin]
  EZ -.-> G

  subgraph 2 [Review]
    G --> H(Peer Review Assigned)
    H --> I[Reviewed by reviewer]
    I --> J(Peer Reviewed)
    I --> K(Senior Reviewed)
    J --> L[Needs review]
    K --> L
    L --> M(Revisited)
    J --> N[No review needed]
  end


  K --> N

  M --> Z[Finalized]
  N --> Z

  subgraph 4 [Machine Actions]
  	T(Any status)
  	T --> V(Machine Updated)
  end

style A fill:#4a8cff,stroke:#333,stroke-width:2px
style B fill:#4a8cff,stroke:#333,stroke-width:2px
style C fill:#bbb,stroke:#333,stroke-width:0px
style D fill:#ff901d,stroke:#333,stroke-width:2px
style DD fill:#bbb,stroke:#333,stroke-width:0px
style E fill:#dc143c,stroke:#333,stroke-width:2px
style F fill:#bbb,stroke:#333,stroke-width:0px
style G fill:#bbb,stroke:#333,stroke-width:0px
style H fill:#60f4c7,stroke:#333,stroke-width:2px
style I fill:#bbb,stroke:#333,stroke-width:0px
style J fill:#61c87b,stroke:#333,stroke-width:2px
style L fill:#bbb,stroke:#333,stroke-width:0px
style N fill:#bbb,stroke:#333,stroke-width:0px
style 0 fill:#eee,stroke:#333,stroke-width:2px
style 1 fill:#6fa8dc,stroke:#333,stroke-width:2px
style 2 fill:#fff888,stroke:#333,stroke-width:2px
style EE fill:#bbb,stroke:#333,stroke-width:0px
style EZ fill:#ffc0cb,stroke:#333,stroke-width:2px
style K fill:#ffc0cb,stroke:#333,stroke-width:2px
style M fill:#a5f2dd,stroke:#333,stroke-width:2px
style T fill:#fff,stroke:#333,stroke-width:2px
style V fill:#a5e2ff,stroke:#333,stroke-width:2px
style Z fill:#000,stroke:#333,stroke-width:2px,color:#fff
```

### List of statuses
- Machine Created
- Human Created
- Assigned
- Updated
- Peer Review Assigned
- Peer Reviewed
- Revisited
- Senior Updated
- Senior Reviewed
- Machine Updated
- Finalized

## Process

### Initial statuses
When Actor/Bulletin/Incident is created in Bayanat, it will have either `Human Created` or `Machine Created` status, depending on whether it was created by a user or automatically imported.

### Analysis
This is the main part of the analysis workflow. Items in this phase are transformed from their raw condition to a processed state that can be filtered and linked to other items in the database.

Administrators or Moderators can assign items to analysts, changing the items status from their initial status to `Assigned`. The assignee can find items under this status and due to be processed using the "Assigned to me" shortcut. After processing these items, their status will be changed to `Updated`. The items can be updated as many times as required in this status by the assignee.

### Review
Peer review is an essential part of the analysis workflow. Not only it is the main tool for quality control of the analysis, in addition, it can be used as a learning tool, especially for new analysts.

Administrators or Moderators can assign items processed by analysts to other analysts for review, using the `Peer Review Assigned` status. At this point the original assignee can't make updates to the item until it's reviewed by the reviewer.

Reviewers can examine items fully, checking all fields completed by the assignee and comparing the data with the source and metadata. This amounts to a mock analysis done by a second pair of eyes. The reviewer can leave comments without making any changes to the data itself.

After the reviewer is done, the status of the item will be changed to `Peer Reviewed`, and the reviewer will need to indicated whether the item required review (contained issues to address) or not. If the item require reviewe, the assignee can make changes to the item to correct any issues, changing the status to `Revisited`. The assignee can also discuss any issues with the reviewer directly or within the team if there's disagreement about the review.

### Senior Actions
Administrators have the ability to make changes to all items in the database. While they are able to choose any status, the convention is to use `Senior Updated` or `Senior Reviewed`.

### Machine Actions
`Machine Updated` status is reserved for actions carried out automatically using a script or a tool within Bayanat.
