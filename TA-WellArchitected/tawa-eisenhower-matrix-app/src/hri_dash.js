import React, { useState } from "react";
import _ from "lodash";
import { Responsive, WidthProvider } from "react-grid-layout";
import { copyToClipboard, replaceHtmlTags } from './utils/utilities';
import { Button, Container, SpaceBetween, Header, Badge, Popover, StatusIndicator, ButtonDropdown,
  Modal, Link, Box, Table, Pagination, CollectionPreferences, PropertyFilter } from "@cloudscape-design/components";
import { useCollection } from '@cloudscape-design/collection-hooks';
import { toolboxGetMatchesCountText, toolboxPaginationLabels, toolboxCollectionPreferencesProps,
  toolboxFilteringProperties, propertyFilterI18nStrings, TableEmptyState, TableNoMatchState } from './utils/toolbox-table-config';
import ta_checks from './data/ta_checks.json';
import sample_data from './data/my_hri.json';
import '@cloudscape-design/global-styles/index.css';
import '/node_modules/react-grid-layout/css/styles.css';
import '/node_modules/react-resizable/css/styles.css';
import './example-styles.css';

const ResponsiveReactGridLayout = WidthProvider(Responsive);

let newFileUpload = false;

const taChecksDetails = ta_checks.checks;

class RiskDetails extends React.Component {
  constructor () {
    super();
    this.state = {
      showModal: false
    };
    
    this.handleOpenModal = this.handleOpenModal.bind(this);
    this.handleCloseModal = this.handleCloseModal.bind(this);
  }
  
  handleOpenModal () {
    this.setState({ showModal: true });
  }
  
  handleCloseModal () {
    this.setState({ showModal: false });
  }
  
  render () {
    const bp_url = 'https://docs.aws.amazon.com/wellarchitected/latest/framework/' + this.props.data.WABestPracticeId + '.html'
    return (
      <div>
        <Button variant="inline-link" onClick={this.handleOpenModal}>More details</Button>
        <Modal
            size={'max'}
            expandToFit={true}
            header={this.props.data.TrustedAdvisorCheckName}
            footer={
              <Box float="right">
                <SpaceBetween direction="horizontal" size="xs">
                  <Popover
                    dismissButton={false}
                    renderWithPortal
                    position="top"
                    size="small"
                    triggerType="custom"
                    content={
                      <StatusIndicator type="success">
                        Raw json copied
                      </StatusIndicator>
                    }
                  >
                    <Button iconName="copy" variant="normal" onClick={() => copyToClipboard(JSON.stringify(this.props.data, undefined, 4))}>Copy</Button>
                  </Popover>
                </SpaceBetween>
              </Box>
            }
            visible={this.state.showModal}
            onDismiss={this.handleCloseModal}
        >
                <Table 
                  columnDefinitions={[
                    {
                      id: "name",
                      header: "Name",
                      cell: (item) => item.TrustedAdvisorCheckName || "-"
                    },
                    {
                      id: "description",
                      header: "Description",
                      cell: (item) => <span>{replaceHtmlTags(item.TrustedAdvisorCheckDesc)}</span> || "-",
                      width: 550
                    },
                    {
                      id: "bestPractice",
                      header: "Best Practice",
                      cell: (item) => (
                        <Link external href={bp_url}>{item.WABestPracticeTitle || "-"}</Link>
                      ),
                      width: 160
                    },
                    {
                      id: "pillar",
                      header: "Pillar",
                      cell: (item) => item.WAPillarId || "-",
                      width: 160
                    },
                    {
                      id: "businessRisk",
                      header: "Business Risk",
                      cell: (item) => 
                        item.WABestPracticeRisk === 'High' ? <StatusIndicator type="error">{item.WABestPracticeRisk}</StatusIndicator>
                          : item.WABestPracticeRisk === 'Medium' ? <StatusIndicator type="warning">{item.WABestPracticeRisk}</StatusIndicator>
                          : item.WABestPracticeRisk === 'Low' ? <StatusIndicator type="info">{item.WABestPracticeRisk}</StatusIndicator>
                          : "-",
                      width: 150
                    },
                    {
                      id: "taCheckStatus",
                      header: "Check Status",
                      cell: (item) => 
                        item.FlaggedResources.status === 'error' ? <StatusIndicator type="error">{item.FlaggedResources.status}</StatusIndicator>
                          : item.FlaggedResources.status === 'warning' ? <StatusIndicator type="warning">{item.FlaggedResources.status}</StatusIndicator>
                          : item.FlaggedResources.status === 'ok' ? <StatusIndicator type="success">{item.FlaggedResources.status}</StatusIndicator>
                          : "-",
                      width: 150
                    },
                    {
                      id: "resource",
                      header: "Resource at Risk",
                      cell: (item) => item.resourceId.split(", ").map((item, index) => index ? <span key={index}><br/>{item}</span> : <span key={index}>{item}</span>) || "-",
                      width: 300
                    },
                  ]}
                  items={[this.props.data]}
                  loadingText="Loading data"
                  sortingDisabled
                  resizableColumns
                  wrapLines
                  empty={
                    <Box
                      margin={{ vertical: "xs" }}
                      textAlign="center"
                      color="inherit"
                    >
                      <SpaceBetween size="m">
                        <b>No data</b>
                      </SpaceBetween>
                    </Box>
                  }
                />
        </Modal>
      </div>
    );
  }
}

function getRisksDataAsCSV(rawRisksData) {
  const replacer = (key, value) => value === null ? '' : value;
  const header = Object.keys(rawRisksData[0]);
  const csvContent = [
    header.join(','),
    ...rawRisksData.map(row => header.map(fieldName => {
      if (fieldName === 'TrustedAdvisorCheckDesc') {
        return(JSON.stringify(row[fieldName], replacer).replace(/,/g, ";"))
      }
      else {
        return(JSON.stringify(row[fieldName], replacer).replace(/,/g, ";"))
      }
    }).join(','))
  ].join('\r\n');
  return 'data:text/csv;charset=utf-8,' + encodeURIComponent(csvContent);
}

function toolboxCreateLabelFunction(columnName) {
  return ({ sorted, descending }) => {
    const sortState = sorted ? `sorted ${descending ? 'descending' : 'ascending'}` : 'not sorted';
    return `${columnName}, ${sortState}.`;
  };
}

export function CollectionHooksTableToolbox({ toolboxItems, onTakeItem, urgencyItemsCount }) {
  const [selectedItems, setSelectedItems] = useState([]);

  const [preferences, setPreferences] = useState({ pageSize: 25, visibleContent: ['name', 'pillar', 'businessRisk', 'taCheckStatus', 'resourceId'] });
  const { items, actions, filteredItemsCount, collectionProps, propertyFilterProps, paginationProps } = useCollection(
    (toolboxItems) ? toolboxItems : [],
    {
      propertyFiltering: {
        filteringProperties: toolboxFilteringProperties,
        empty: <TableEmptyState resourceName="data" />,
        noMatch: (
          <TableNoMatchState
            onClearFilter={() => {
              actions.setPropertyFiltering({ tokens: [], operation: 'and' });
            }}
          />
        ),
      },
      pagination: { pageSize: preferences.pageSize },
      sorting: {},
      selection: { keepSelection: true },
    }
  );

  const toolboxFullColumnDefinitions = [
    {
      id: "name",
      header: "Name",
      cell: (item) => 
        <SpaceBetween direction="horizontal" size="xs">
          <Button variant="normal" onClick={onTakeItem.bind(undefined, item)}>
              {item.TrustedAdvisorCheckName}
          </Button>
          <Popover
              dismissButton={false}
              position="top"
              size="large"
              triggerType="custom"
              renderWithPortal
              content={
                <Box variant="p">
                  {replaceHtmlTags(item.TrustedAdvisorCheckDesc)}
                </Box>
              }
          >
            <Button iconName="status-info" variant="icon"></Button>
          </Popover>
        </SpaceBetween> || "-",
      ariaLabel: toolboxCreateLabelFunction('Name'),
      sortingField: 'TrustedAdvisorCheckName',
      width: 450
    },
    {
      id: "description",
      header: "Description",
      cell: (item) => <span>{replaceHtmlTags(item.TrustedAdvisorCheckDesc)}</span> || "-",
      ariaLabel: toolboxCreateLabelFunction('Description'),
      sortingField: 'TrustedAdvisorCheckDesc'
    },
    {
      id: "bestPractice",
      header: "Best Practice",
      cell: (item) => (
        <Link external href={'https://docs.aws.amazon.com/wellarchitected/latest/framework/' + item.WABestPracticeId + '.html'}>{item.WABestPracticeTitle || "-"}</Link>
      ),
      ariaLabel: toolboxCreateLabelFunction('Best Practice'),
      sortingField: 'WABestPracticeId'
    },
    {
      id: "pillar",
      header: "Pillar",
      cell: (item) => item.WAPillarId || "-",
      ariaLabel: toolboxCreateLabelFunction('Pillar'),
      sortingField: 'WAPillarId',
      width: 160
    },
    {
      id: "businessRisk",
      header: "Business Risk",
      cell: (item) => 
        item.WABestPracticeRisk === 'High' ? <StatusIndicator type="error">{item.WABestPracticeRisk}</StatusIndicator>
          : item.WABestPracticeRisk === 'Medium' ? <StatusIndicator type="warning">{item.WABestPracticeRisk}</StatusIndicator>
          : item.WABestPracticeRisk === 'Low' ? <StatusIndicator type="info">{item.WABestPracticeRisk}</StatusIndicator>
          : "-",
      ariaLabel: toolboxCreateLabelFunction('Business Risk'),
      sortingField: 'WABestPracticeRisk',
      width: 150
    },
    {
      id: "taCheckStatus",
      header: "Check Status",
      cell: (item) => 
        item.resultStatus === 'error' ? <StatusIndicator type="error">{item.resultStatus}</StatusIndicator>
          : item.resultStatus === 'warning' ? <StatusIndicator type="warning">{item.resultStatus}</StatusIndicator>
          : item.resultStatus === 'ok' ? <StatusIndicator type="success">{item.resultStatus}</StatusIndicator>
          : "-",
      ariaLabel: toolboxCreateLabelFunction('Check Status'),
      sortingField: 'resultStatus',
      width: 150
    },
    {
        id: "resourceId",
        header: "Resource at Risk",
        cell: (item) => item.resourceId.split(", ").map((resource, index) => index ? <span key={index}><br/>{resource}</span> : <span key={index}>{resource}</span>) || "-",
        ariaLabel: toolboxCreateLabelFunction('Resource at Risk')
    },
    {
      id: "resourceRaw",
      header: "Resource at Risk (Raw)",
      cell: (item) => JSON.stringify(item.FlaggedResources, null, 4) || "-",
      ariaLabel: toolboxCreateLabelFunction('Resource at Risk (Raw)')
    },
    {
      id: "region",
      header: "Region",
      cell: (item) => item.region || "-",
      ariaLabel: toolboxCreateLabelFunction('Region'),
      sortingField: 'region'
    },
  ];

  return (
    <Table
      {...collectionProps}
      columnDefinitions={toolboxFullColumnDefinitions}
      visibleColumns={preferences.visibleContent}
      selectionType="multi"
      selectedItems={selectedItems}
      onSelectionChange={evt => setSelectedItems(evt.detail.selectedItems)}
      wrapLines
      resizableColumns
      stickyHeader
      variant="borderless"
      items={items}
      contentDensity="comfortable"
      pagination={<Pagination {...paginationProps} ariaLabels={toolboxPaginationLabels} />}
      filter={
        <PropertyFilter
          {...propertyFilterProps}
          i18nStrings={propertyFilterI18nStrings}
          countText={toolboxGetMatchesCountText(filteredItemsCount)}
          expandToViewport={true}
        />
      }
      preferences={
        <CollectionPreferences
          {...toolboxCollectionPreferencesProps}
          preferences={preferences}
          onConfirm={({ detail }) => setPreferences(detail)}
          pageSizePreference={{
            options: [
              { value: 25, label: "25 checks" },
              { value: 50, label: "50 checks" },
              { value: 75, label: "75 checks" },
              { value: 100, label: "100 checks" }
            ]
          }}
        />
      }
      header={
        <Header
          variant="h2"
          actions={
            <SpaceBetween
              direction="horizontal"
              size="xs"
            >
              <Button 
                disabled={selectedItems.length === 0}
                onClick={() => {
                    for (let i = 0; i < selectedItems.length; i++) {
                      onTakeItem.bind(undefined, selectedItems[i])()
                    }
                    setSelectedItems([]);
                }}
              >
                Add all selected {selectedItems.length && filteredItemsCount
                  ? "(" + selectedItems.length + "/" + filteredItemsCount + ")"
                  : selectedItems.length ? "(" + selectedItems.length + "/" + toolboxItems.length + ")"
                  : filteredItemsCount ? "(" + filteredItemsCount + ")"
                  : "(" + toolboxItems.length + ")"}
              </Button>
            </SpaceBetween>
          }
        >
          <SpaceBetween
                  direction="horizontal"
                  size="xxl"
                >
                  <span>Trusted Advisor Checks </span>
                  <Badge color="red">High Urgency: {urgencyItemsCount.highUrgencyItemsCount}</Badge>
                  <Badge color="grey">Medium Urgency: {urgencyItemsCount.mediumUrgencyItemsCount}</Badge>
                  <Badge color="green">Low Urgency: {urgencyItemsCount.lowUrgencyItemsCount}</Badge>
            </SpaceBetween>
        </Header>
      }
    />
  );
}

class RisksFullTable extends React.Component {
  constructor () {
    super();
    this.state = {
      showModal: false
    };
    
    this.handleOpenModal = this.handleOpenModal.bind(this);
    this.handleCloseModal = this.handleCloseModal.bind(this);
  }

  handleOpenModal () {
    this.setState({ showModal: true });
  }
  
  handleCloseModal () {
    this.setState({ showModal: false });
    newFileUpload = false;
  }

  render () {
    return (
      <div>
        <Button 
          variant="normal" 
          onClick={this.handleOpenModal}
          disabled={this.props.risksData === null}
        >
            Open Risks Table
        </Button>
        <Modal
            size={'max'}
            expandToFit={true}
            footer={
              <Box float="right">
                <SpaceBetween direction="horizontal" size="xs">
                  <Button iconName="download" variant="normal" onClick={() => {const currentTime = new Date();
                    const dataDownloadToCSV = getRisksDataAsCSV(this.props.risksData);
                    var link = document.createElement('a');
                    link.setAttribute('href', dataDownloadToCSV);
                    link.setAttribute('download', 'riskData_' + currentTime.toISOString() + '_UTC.csv');
                    document.body.appendChild(link);
                    link.click();}}
                  >Download CSV</Button>
                  <Popover
                      dismissButton={false}
                      position="top"
                      size="small"
                      triggerType="custom"
                      renderWithPortal
                      content={
                        <StatusIndicator type="success">
                          Raw json copied
                        </StatusIndicator>
                      }
                  >
                    <Button iconName="copy" variant="normal" onClick={() => copyToClipboard(JSON.stringify(this.props.risksData, undefined, 4))}>Copy All</Button>
                  </Popover>
                  <Button variant="primary" onClick={this.handleCloseModal}>Close</Button>
                </SpaceBetween>
              </Box>
            }
            visible={this.state.showModal || newFileUpload}
            onDismiss={this.handleCloseModal}
        >
          <CollectionHooksTableToolbox toolboxItems={this.props.toolboxItems || []} onTakeItem={this.props.onTakeItem} urgencyItemsCount={this.props.urgencyItemsCount} />
        </Modal>
      </div>
    );
  }
}

export default class ToolboxLayout extends React.Component {
  static defaultProps = {
    className: "layout",
    rowHeight: 30,
    onLayoutChange: function() {},
    cols: { lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 },
    initialLayout: generateLayout()
  };

  state = {
    currentBreakpoint: "lg",
    compactType: null,
    layouts: { lg: this.props.initialLayout },
    toolbox: { lg: [] },
    risksData: null
  };

  componentDidMount() {
    risksInit(this);
  }

  generateDOM() {
    return _.map(this.state.layouts[this.state.currentBreakpoint], l => {
      return (
        <div key={l.i}>
          <div className="hide-button">
            <Button iconName="close" variant="icon" onClick={this.onPutItem.bind(this, l)}/>
          </div>
          <Container
            disableHeaderPaddings
          >
            {this.state.risksData[l.i].FlaggedResources.status === 'error' ? <Box textAlign="center" variant="h3" color="text-status-error">{this.state.risksData[l.i].TrustedAdvisorCheckName}</Box>
                  : this.state.risksData[l.i].FlaggedResources.status === 'warning' ? <Box textAlign="center" variant="h3" color="text-status-warning">{this.state.risksData[l.i].TrustedAdvisorCheckName}</Box>
                  : this.state.risksData[l.i].FlaggedResources.status === 'ok' ? <Box textAlign="center" variant="h3" color="text-status-success">{this.state.risksData[l.i].TrustedAdvisorCheckName}</Box>
                  : "-"}
            <SpaceBetween
              alignItems="center"
              direction="vertical"
              size="xs"
            >
              <Box 
                variant="p"
                color={this.state.risksData[l.i].FlaggedResources.status === 'error' ? "text-status-error"
                : this.state.risksData[l.i].FlaggedResources.status === 'warning' ? "text-status-warning"
                : this.state.risksData[l.i].FlaggedResources.status === 'ok' ? "text-status-success" : "inherit"}
              >
                {this.state.risksData[l.i].resourceId.split(", ").map((item, index) => index ? <span key={index}><br/>{item}</span> : <span key={index}>{item}</span>)}
              </Box>
              <RiskDetails data={this.state.risksData[l.i]}/>
            </SpaceBetween>
          </Container>
        </div>
      );
    });
  }

  onBreakpointChange = breakpoint => {
    this.setState(prevState => ({
      currentBreakpoint: breakpoint,
      toolbox: {
        ...prevState.toolbox,
        [breakpoint]:
          prevState.toolbox[breakpoint] ||
          prevState.toolbox[prevState.currentBreakpoint] ||
          []
      }
    }));
  };

  onTakeItem = item => {
    this.setState(prevState => ({
      toolbox: {
        ...prevState.toolbox,
        [prevState.currentBreakpoint]: prevState.toolbox[
          prevState.currentBreakpoint
        ].filter(({ i }) => i !== item.i)
      },
      layouts: {
        ...prevState.layouts,
        [prevState.currentBreakpoint]: [
          ...prevState.layouts[prevState.currentBreakpoint],
          item
        ]
      }
    }));
  };

  onPutItem = item => {
    item.TrustedAdvisorCheckId = this.state.risksData[item.i].TrustedAdvisorCheckId;
    item.TrustedAdvisorCheckName = this.state.risksData[item.i].TrustedAdvisorCheckName;
    item.TrustedAdvisorCheckDesc = this.state.risksData[item.i].TrustedAdvisorCheckDesc;
    item.WAPillarId = this.state.risksData[item.i].WAPillarId;
    item.WAQuestionId = this.state.risksData[item.i].WAQuestionId;
    item.WABestPracticeId = this.state.risksData[item.i].WABestPracticeId;
    item.WABestPracticeTitle = this.state.risksData[item.i].WABestPracticeTitle;
    item.WABestPracticeDesc = this.state.risksData[item.i].WABestPracticeDesc;
    item.WABestPracticeRisk = this.state.risksData[item.i].WABestPracticeRisk;
    item.resourceId = this.state.risksData[item.i].resourceId;
    item.resultStatus = this.state.risksData[item.i].FlaggedResources.status;
    item.region = this.state.risksData[item.i].FlaggedResources.region;
    item.uniqueId = this.state.risksData[item.i].uniqueI;
    item.FlaggedResources = this.state.risksData[item.i].FlaggedResources;
    this.setState(prevState => {
      return {
        toolbox: {
          ...prevState.toolbox,
          [prevState.currentBreakpoint]: [
            ...(prevState.toolbox[prevState.currentBreakpoint] || []),
            item
          ]
        },
        layouts: {
          ...prevState.layouts,
          [prevState.currentBreakpoint]: prevState.layouts[
            prevState.currentBreakpoint
          ].filter(({ i }) => i !== item.i)
        }
      };
    });
  };

  onLayoutChange = (layout, layouts) => {
    this.props.onLayoutChange(layout, layouts);
    this.setState({ layouts });
  };

  resetLayout = () => {
    this.setState({
      layouts: { lg: [] },
      toolbox: { lg: [] },
      risksData: null
    });
  }

  parseCheckMetadata = (checkId, checkFlaggedResourcesMetadata) => {
    let index = taChecksDetails.findIndex(check => check.id === checkId);
    let resourceId = '';
    if (index !== -1) {
      for (let i = 0; i < taChecksDetails[index].metadata.length; i++) {
        resourceId = resourceId + taChecksDetails[index].metadata[i] + ": " + checkFlaggedResourcesMetadata[i] + ", "
      }
      resourceId = resourceId.slice(0, -2)
    }
    else {
      resourceId = checkFlaggedResourcesMetadata.join(", ")
    }
    return resourceId
  }

  expandFlaggedResources = (risksData) => {
    let expandedRisksData = [];
    for (let i = 0; i < risksData.length; i++) {
      for (let n = 0; n < risksData[i].FlaggedResources.length; n++) {
        let tmpRisksObject = JSON.parse(JSON.stringify(risksData[i]));
        tmpRisksObject.FlaggedResources = risksData[i].FlaggedResources[n];
        tmpRisksObject.resourceId = (risksData[i].FlaggedResources[n].metadata) ? this.parseCheckMetadata(risksData[i].TrustedAdvisorCheckId, risksData[i].FlaggedResources[n].metadata) : '';
        tmpRisksObject.uniqueId = risksData[i].TrustedAdvisorCheckId + "_" + risksData[i].FlaggedResources[n].resourceId
        expandedRisksData.push(tmpRisksObject);
      }
    }
    return expandedRisksData
  }

  loadSampleData = () => {
    let expandedRisksData = this.expandFlaggedResources(sample_data);
    let layout = generateLayout(true, expandedRisksData);
    this.setState({
      layouts: { lg: layout },
      risksData: expandedRisksData
    });
    risksInit(this);
    newFileUpload = true;
  }

  uploadFile = (event) => {
    let file = event.target.files[0];
    this.resetLayout();
    
    if (file) {
      let fileReader = new FileReader(); 
      fileReader.readAsText(file); 
      fileReader.onload = () => {
        let expandedRisksData = this.expandFlaggedResources(JSON.parse(fileReader.result));
        let layout = generateLayout(true, expandedRisksData);
        this.setState({
          layouts: { lg: layout },
          risksData: expandedRisksData
        });
        risksInit(this);
        newFileUpload = true;
      }; 
      fileReader.onerror = () => {
        console.log(fileReader.error);
      }; 
    }
  }

  getHighUrgencyItems = (items) => {
    let highUrgencyItems = [];
    for (let i = 0; i < items.length; i++) {
      if (this.state.risksData[items[i].i].FlaggedResources.status === 'error') {
        highUrgencyItems.push(items[i]);
      }
    }
    return highUrgencyItems
  }

  getMediumUrgencyItems = (items) => {
    let mediumUrgencyItems = [];
    for (let i = 0; i < items.length; i++) {
      if (this.state.risksData[items[i].i].FlaggedResources.status === 'warning') {
        mediumUrgencyItems.push(items[i]);
      }
    }
    return mediumUrgencyItems
  }

  getLowUrgencyItems = (items) => {
    let lowUrgencyItems = [];
    for (let i = 0; i < items.length; i++) {
      if (this.state.risksData[items[i].i].FlaggedResources.status === 'ok') {
        lowUrgencyItems.push(items[i]);
      }
    }
    return lowUrgencyItems
  }

  render() {
    let highUrgencyItems = this.getHighUrgencyItems(this.state.toolbox[this.state.currentBreakpoint] || []);
    let mediumUrgencyItems = this.getMediumUrgencyItems(this.state.toolbox[this.state.currentBreakpoint] || []);
    let lowUrgencyItems = this.getLowUrgencyItems(this.state.toolbox[this.state.currentBreakpoint] || []);
    let urgencyItemsCount={highUrgencyItemsCount: highUrgencyItems.length, mediumUrgencyItemsCount: mediumUrgencyItems.length, lowUrgencyItemsCount: lowUrgencyItems.length};

    let highUrgencyItemsInLayouts = this.getHighUrgencyItems(this.state.layouts[this.state.currentBreakpoint] || []);
    let mediumUrgencyItemsInLayouts = this.getMediumUrgencyItems(this.state.layouts[this.state.currentBreakpoint] || []);
    let lowUrgencyItemsInLayouts = this.getLowUrgencyItems(this.state.layouts[this.state.currentBreakpoint] || []);
    let urgencyItemsCountInLayouts={highUrgencyItemsCount: highUrgencyItemsInLayouts.length, mediumUrgencyItemsCount: mediumUrgencyItemsInLayouts.length, lowUrgencyItemsCount: lowUrgencyItemsInLayouts.length};
    return (
      <div>
        <Container
          fitHeight={true}
          disableContentPaddings
          header={
            <Header
              variant="h2"
              actions={
                <SpaceBetween
                  direction="horizontal"
                  size="xs"
                >
                  <RisksFullTable toolboxItems={this.state.toolbox[this.state.currentBreakpoint] || []} onTakeItem={this.onTakeItem} risksData={this.state.risksData} urgencyItemsCount={urgencyItemsCount}/>
                  <Button variant="primary" iconName={"upload"}>
                    <input className="inputButton hidden" type={"file"} accept={".json"} onChange={this.uploadFile} />
                    Upload json file
                  </Button>
                  <ButtonDropdown
                    expandToViewport
                    items={[
                      { id: "load-sample", text: "Load Sample Data", disabled: this.state.risksData !== null }
                    ]}
                    ariaLabel="Load Data Options"
                    variant="icon"
                    onItemClick={this.loadSampleData}
                  />
                </SpaceBetween>
              }
            >
              {urgencyItemsCountInLayouts.highUrgencyItemsCount + urgencyItemsCountInLayouts.mediumUrgencyItemsCount + urgencyItemsCountInLayouts.lowUrgencyItemsCount !== 0 ?
              <SpaceBetween
                  direction="horizontal"
                  size="xxl"
                >
                  <span>Trusted Advisor Checks</span>
                  <Badge color="red">High Urgency: {urgencyItemsCountInLayouts.highUrgencyItemsCount}</Badge>
                  <Badge color="grey">Medium Urgency: {urgencyItemsCountInLayouts.mediumUrgencyItemsCount}</Badge>
                  <Badge color="green">Low Urgency: {urgencyItemsCountInLayouts.lowUrgencyItemsCount}</Badge>
              </SpaceBetween> :
              <SpaceBetween
                  direction="horizontal"
                  size="xxl"
                >
                  <span>Trusted Advisor Checks</span>
              </SpaceBetween> }
            </Header>
          }
        >
        </Container>

        <div className="yAxisTop">High Impact</div>
        <div className="yAxisBottom">Low Impact</div>
        <div className="xAxisLeft">High Urgency</div>
        <div className="xAxisRight">Low Urgency</div>
        <div className="verticalLine"></div>
        <hr width="98%" color="gray" className="horizontalLine"></hr>

        <div className="doItNow">Do it Now</div>
        <div className="doItNext">Do it Next</div>
        <div className="scheduleFirst">Schedule it First</div>
        <div className="scheduleLast">Schedule it Last</div>
        <ResponsiveReactGridLayout
          {...this.props}
          layouts={this.state.layouts}
          onBreakpointChange={this.onBreakpointChange}
          onLayoutChange={this.onLayoutChange}
          measureBeforeMount={false}
          useCSSTransforms={false}
          compactType={this.state.compactType}
          preventCollision={!this.state.compactType}
          allowOverlap={true}
        >
          {this.generateDOM()}
        </ResponsiveReactGridLayout>
      </div>
    );
  }
}

function risksInit(currentState) {
    currentState.setState(prevState => {
        return {
          toolbox: {
            ...prevState.layouts,
            [prevState.currentBreakpoint]: [
              ...(prevState.layouts[prevState.currentBreakpoint] || [])
            ]
          },
          layouts: {
            ...prevState.toolbox,
            [prevState.currentBreakpoint]: prevState.toolbox[
              prevState.currentBreakpoint
            ]
          }
        };
      });
    return
}

function generateLayout(uploaded=false,risksData=null) {
    if (uploaded === false) {
        return [];
    } else {
      let risksLength = risksData.length;
      return _.map(_.range(0, risksLength), function(item, i) {
          return {
          x: 5,
          y: 9,
          w: 2,
          h: 2,
          i: i.toString(),
          static: false,
          TrustedAdvisorCheckId: risksData[i].TrustedAdvisorCheckId,
          TrustedAdvisorCheckName: risksData[i].TrustedAdvisorCheckName,
          TrustedAdvisorCheckDesc: risksData[i].TrustedAdvisorCheckDesc,
          WAPillarId: risksData[i].WAPillarId,
          WAQuestionId: risksData[i].WAQuestionId,
          WABestPracticeId: risksData[i].WABestPracticeId,
          WABestPracticeTitle: risksData[i].WABestPracticeTitle,
          WABestPracticeDesc: risksData[i].WABestPracticeDesc,
          WABestPracticeRisk: risksData[i].WABestPracticeRisk,
          resourceId: risksData[i].resourceId,
          resultStatus: risksData[i].FlaggedResources.status,
          region: risksData[i].FlaggedResources.region,
          uniqueId: risksData[i].uniqueId,
          FlaggedResources: risksData[i].FlaggedResources
          };
      });
    }
}