import * as React from 'react';
import { Link, Box, SpaceBetween, Button } from '@cloudscape-design/components';
import { replaceHtmlTags } from './utilities';

export function toolboxGetMatchesCountText(count) {
  return count === 1 ? `1 match` : `${count} matches`;
}

function toolboxCreateLabelFunction(columnName) {
  return ({ sorted, descending }) => {
    const sortState = sorted ? `sorted ${descending ? 'descending' : 'ascending'}` : 'not sorted';
    return `${columnName}, ${sortState}.`;
  };
}

const toolboxFullColumnDefinitions = [
  {
    id: "name",
    header: "Name",
    cell: (item) => <span>[{parseInt(item.i) + 1}] {item.TrustedAdvisorCheckName} ({item.resourceId}) || "-"</span>,
    ariaLabel: toolboxCreateLabelFunction('Name'),
    sortingField: 'name'
  },
  {
    id: "description",
    header: "Description",
    cell: (item) => <span>{replaceHtmlTags(item.TrustedAdvisorCheckDesc)}</span> || "-",
    ariaLabel: toolboxCreateLabelFunction('Description'),
    sortingField: 'description'
  },
  {
    id: "bestPractice",
    header: "Best Practice",
    cell: (item) => (
      <Link external href={'https://docs.aws.amazon.com/wellarchitected/latest/framework/' + item.WABestPracticeId + '.html'}>{item.WABestPracticeTitle || "-"}</Link>
    ),
    ariaLabel: toolboxCreateLabelFunction('Best Practice'),
    sortingField: 'bestPractice'
  },
  {
    id: "pillar",
    header: "Pillar",
    cell: (item) => item.WAPillarId || "-",
    ariaLabel: toolboxCreateLabelFunction('Pillar'),
    sortingField: 'pillar'
  },
  {
    id: "businessRisk",
    header: "Business Risk",
    cell: (item) => item.WABestPracticeRisk || "-",
    ariaLabel: toolboxCreateLabelFunction('Business Risk'),
    sortingField: 'businessRisk'
  },
  {
    id: "taCheckStatus",
    header: "Check Status",
    cell: (item) => item.resultStatus || "-",
    ariaLabel: toolboxCreateLabelFunction('Check Status'),
    sortingField: 'taCheckStatus'
  },
  {
      id: "resourceId",
      header: "Resource at Risk",
      cell: (item) => item.resourceId || "-",
      ariaLabel: toolboxCreateLabelFunction('Resource at Risk'),
      sortingField: 'resourceId'
  },
  {
    id: "resourceRaw",
    header: "Resource at Risk (Raw)",
    cell: (item) => JSON.stringify(item.FlaggedResources, null, 4) || "-",
    ariaLabel: toolboxCreateLabelFunction('Resource at Risk (Raw)'),
    sortingField: 'resourceRaw'
  },
];

export const toolboxPaginationLabels = {
  nextPageLabel: 'Next page',
  pageLabel: pageNumber => `Go to page ${pageNumber}`,
  previousPageLabel: 'Previous page',
};

const pageSizePreference = {
  title: 'Select page size',
  options: [
    { value: 10, label: '10 resources' },
    { value: 20, label: '20 resources' },
  ],
};

const visibleContentPreference = {
  title: 'Select visible content',
  options: [
    {
      label: 'Main properties',
      options: toolboxFullColumnDefinitions.map(({ id, header }) => ({ id, label: header, editable: id !== 'name' })),
    },
  ],
};

export const toolboxCollectionPreferencesProps = {
  pageSizePreference,
  visibleContentPreference,
  cancelLabel: 'Cancel',
  confirmLabel: 'Confirm',
  title: 'Preferences',
};

export const toolboxFilteringProperties = [
  {
    propertyLabel: 'Name',
    key: 'TrustedAdvisorCheckName',
    groupValuesLabel: 'Name values',
    operators: [':', '!:', '=', '!=', '^'],
  },
  {
    propertyLabel: 'Best Practice',
    key: 'WABestPracticeId',
    groupValuesLabel: 'Best Practice values',
    operators: [':', '!:', '=', '!=', '^'],
  },
  {
    propertyLabel: 'Pillar',
    key: 'WAPillarId',
    groupValuesLabel: 'Pillar values',
    operators: [':', '!:', '=', '!=', '^'],
  },
  {
    propertyLabel: 'Business Risk',
    key: 'WABestPracticeRisk',
    groupValuesLabel: 'Business Risk values',
    operators: [':', '!:', '=', '!=', '^'],
  },
  {
    propertyLabel: 'Check Status',
    key: 'resultStatus',
    groupValuesLabel: 'Check Status values',
    operators: [':', '!:', '=', '!=', '^'],
  },
  {
    propertyLabel: 'Resource at Risk',
    key: 'resourceId',
    groupValuesLabel: 'Resource at Risk values',
    operators: [':', '!:', '=', '!=', '^'],
  },
  {
    propertyLabel: 'Region',
    key: 'region',
    groupValuesLabel: 'Region values',
    operators: [':', '!:', '=', '!=', '^'],
  },
];

export const propertyFilterI18nStrings = {
  filteringAriaLabel: "Find checks",
  filteringPlaceholder: "Find checks",
  clearFiltersText: "Clear filters",
  cancelActionText: "Cancel",
  applyActionText: "Apply",
  operationAndText: "and",
  operationOrText: "or",
  operatorContainsText: "Contains",
  operatorDoesNotContainText: "Does not contain",
  operatorEqualsText: "Equals",
  operatorDoesNotEqualText: "Does not equal",
  operatorStartsWithText: "Starts with",
};

export const TableEmptyState = ({ resourceName }) => (
  <Box margin={{ vertical: 'xs' }} textAlign="center" color="inherit">
    <SpaceBetween size="xxs">
      <div style={{height: 70 + 'px'}}>
        <b>No {resourceName.toLowerCase()} loaded</b>
      </div>
    </SpaceBetween>
  </Box>
);

export const TableNoMatchState = ({ onClearFilter }) => (
  <Box margin={{ vertical: 'xs' }} textAlign="center" color="inherit">
    <SpaceBetween size="xxs">
      <div>
        <b>No matches</b>
      </div>
      <Button onClick={onClearFilter}>Clear filter</Button>
    </SpaceBetween>
  </Box>
);
