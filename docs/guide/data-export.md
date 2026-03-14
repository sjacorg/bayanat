# Data Export

Export items from the database to multiple formats, optionally including related media files.

## Enabling

The export tool must be enabled in the environment configuration. See [Configuration](/deployment/configuration) for details.

## Permissions

- All administrators can make export requests
- Individual users can be granted the `Can Request Exports` permission
- Only administrators can approve or reject export requests

## Output Formats

| Format | Actor | Bulletin | Incident |
| --- | --- | --- | --- |
| PDF | Yes | Yes | Yes |
| JSON | Yes | Yes | Yes |
| CSV | Yes | Yes | No |
| Media | Yes | Yes | No |

PDF exports include all item fields and metadata in a formatted document. JSON exports contain the full structured data. CSV exports provide tabular data suitable for spreadsheet analysis. Media exports bundle all attached files.

## Workflow

```mermaid
%%{ init: { 'flowchart': { 'curve': 'basis', 'htmlLabels': false} } }%%
graph TB

	subgraph 0 [ Permission ]
		A[Admin]
		B[Users with 'Can Request Exports' permission]
  end

  A & B --> C

	subgraph 1 [ Request ]
  	C(Select items to export)
    C --> D(Choose output format and whether or not to include media)
    D --> E(Submit export request for approval)

  end

  E --> G(Sent to Export dashboard for approval by admin)
  G --> H
  G --> I

  subgraph 2 [Approval]
    I{Approved}
    H{Rejected}

    I -.-> L[Admin can reject requests after approval]
    L -.-> H
  end

  I ----> J(Export generated)
  J --> K(Download link ready)
  K --> T

  subgraph 3 [Download]
  	T(User can view own requests in export dashboard)
  	T --> V(Approved requested can be downloaded before expiry time)
    V -..-> X(Admin can change expiry time of request)
    X -..-> V
  end

  V ----> M(Request expires at the expiry time)
  M --> Y

  subgraph 4 [Expiry]
    Y((Expired))
    Y --> Z(Request can no longer be downloaded and expiry date cannot be changed)
    Z --> ZZ(Export files are deleted)
  end

style A fill:#4a8cff,stroke:#333,stroke-width:2px
style B fill:#4a8cff,stroke:#333,stroke-width:2px
style C fill:#ddd,stroke:#333,stroke-width:2px
style D fill:#ddd,stroke:#333,stroke-width:2px
style E fill:#ddd,stroke:#333,stroke-width:2px
style G fill:#bbb,stroke:#333,stroke-width:2px
style H fill:#dc143c,stroke:#333,stroke-width:2px
style I fill:#61c87b,stroke:#333,stroke-width:2px
style J fill:#61c87b,stroke:#333,stroke-width:2px
style L fill:#bbb,stroke:#333,stroke-width:2px
style 0 fill:#eee,stroke:#333,stroke-width:2px
style 1 fill:#6fa8dc,stroke:#333,stroke-width:2px
style 2 fill:#fff888,stroke:#333,stroke-width:2px
style 3 fill:#61c87b,stroke:#333,stroke-width:2px
style 4 fill:#ccc,stroke:#333,stroke-width:2px
style K fill:#61c87b,stroke:#333,stroke-width:2px
style M fill:#aaa,stroke:#333,stroke-width:2px
style T fill:#fff,stroke:#333,stroke-width:2px
style V fill:#fff,stroke:#333,stroke-width:2px
style X fill:#fff,stroke:#333,stroke-width:2px
style Y fill:#000,stroke:#fff,stroke-width:5px,color:#fff
style Z fill:#000,stroke:#333,stroke-width:2px,color:#fff
style ZZ fill:#000,stroke:#333,stroke-width:2px,color:#fff
```

1. Select items from the data table
2. Choose the export format and whether to include media
3. Submit the export request
4. An administrator reviews and approves or rejects the request
5. Once approved, the export file is available for download
6. Exports have an expiry time, after which they can no longer be downloaded and files are deleted

Administrators can adjust the expiry time or expire an export immediately if needed.

## Security

Export requests go through an approval workflow to prevent unauthorized data extraction. All export activity is logged in the [Activity Monitor](/guide/activity).

::: tip
The Data Export Tool was made possible by funding from the [International Coalition of Sites of Conscience](https://www.sitesofconscience.org/).
:::
